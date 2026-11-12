#!/usr/bin/env python3
"""Read-only pre-scan for App Store readiness audits.

Collects deterministic facts about an iOS project (Expo, React Native, or a native
Swift/Objective-C Xcode project): layout, native configuration, purpose strings,
privacy manifests, signal dependencies, build toolchain, background modes, secrets,
and code leads for each audit domain.

It never edits the project, never builds it, and makes no network requests.
  --introspect  runs `npx --no-install expo config --type introspect --json`, which
                evaluates the project's app config (project code) but writes no files.
  --ipa PATH    reads a built .ipa, .xcarchive, or .app to see what actually shipped.

The output is a lead sheet, not a verdict. Every signal needs someone to read the
code before it becomes a finding.

Usage:
  python3 scan.py [PROJECT_DIR] [--introspect] [--ipa PATH]
                  [--format json|md] [--out FILE] [--fail-on blocker|never]
                  [--max-hits N] [--today YYYY-MM-DD]

Exit codes: 0 done; 1 blocking signals found with --fail-on blocker; 2 usage error.
"""

import argparse
import datetime as dt
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

TOOL_VERSION = "3.0.0"
SCHEMA = "better-app-store-review/scan@1"
FACTS_PATH = Path(__file__).resolve().parent.parent / "references" / "facts.json"

SKIP_DIRS = {"node_modules", "Pods", ".git", "build", "DerivedData", ".expo", "dist",
             ".next", "vendor", "Carthage", ".gradle", "__pycache__", ".turbo", ".yarn",
             "coverage", ".build"}
APP_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".swift", ".m", ".mm", ".h"}
BACKEND_EXT = {".java", ".kt", ".kts", ".py", ".go", ".rb", ".php", ".ts", ".js", ".mjs",
               ".cjs", ".cs", ".rs", ".scala"}
TEST_MARKERS = ("__tests__", "__mocks__", ".test.", ".spec.", "/test/", "/tests/",
                "/src/test/", "UITests", "Tests/", ".stories.")
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
             "Podfile.lock", "Package.resolved", "Gemfile.lock", "poetry.lock", "go.sum"}
MAX_FILE_BYTES = 1_500_000

BACKEND_MARKERS = {"pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "pyproject.toml",
                   "requirements.txt", "Gemfile", "composer.json", "firebase.json",
                   "serverless.yml", "serverless.yaml", "Cargo.toml"}
SERVER_DEPS = ("express", "fastify", "@nestjs/core", "koa", "hono", "@hapi/hapi")

SIGNAL_GROUPS = {
    "payments": ["iap", "purchases", "revenuecat", "superwall", "adapty", "qonversion",
                 "stripe", "paypal", "braintree"],
    "tracking_ads": ["tracking-transparency", "fbsdk", "facebook", "appsflyer", "adjust",
                     "branch", "singular", "kochava", "tiktok", "snapchat",
                     "google-mobile-ads", "googlemobileads", "admob", "applovin",
                     "ironsource", "unity-ads", "unityads", "vungle", "chartboost",
                     "inmobi", "firebase/analytics", "firebaseanalytics"],
    "analytics_replay": ["posthog", "amplitude", "mixpanel", "segment", "rudderstack",
                         "sentry", "bugsnag", "datadog", "instabug", "logrocket",
                         "fullstory", "smartlook", "uxcam", "clarity", "heap"],
    "third_party_ai": ["openai", "anthropic", "generative-ai", "google/genai",
                       "generativeai", "perplexity", "replicate", "huggingface", "groq",
                       "mistral", "cohere", "deepseek", "together-ai", "@ai-sdk",
                       "langchain", "elevenlabs", "deepgram", "assemblyai", "stability"],
    "health": ["healthkit", "react-native-health", "health-connect", "pedometer",
               "expo-sensors", "coremotion"],
    "accounts": ["google-signin", "googlesignin", "fbsdklogin", "auth-session",
                 "apple-authentication", "app-auth", "appauth", "clerk", "auth0",
                 "firebase/auth", "firebaseauth", "supabase", "local-authentication",
                 "biometrics"],
    "permissions_media": ["location", "geolocation", "camera", "contacts", "calendar",
                          "media-library", "image-picker", "document-picker", "expo-av",
                          "expo-audio", "expo-video", "voice", "speech", "ble-",
                          "bluetooth", "nfc", "permissions"],
    "engagement": ["notifications", "messaging", "onesignal", "notifee", "store-review",
                   "in-app-review", "musickit", "apple-music", "game-center", "gamekit",
                   "weather", "live-activit", "widget", "apple-targets", "siri"],
    "webview": ["webview"],
    "ota_flags": ["expo-updates", "code-push", "codepush", "revopush", "hot-updater",
                  "remote-config", "remoteconfig", "launchdarkly", "statsig",
                  "growthbook", "configcat", "flagsmith", "unleash"],
}

# (dependency substrings, required Info.plist keys; "A|B" means either key satisfies it)
EXPECTED_KEYS = [
    (("expo-camera", "vision-camera", "react-native-camera"), ["NSCameraUsageDescription"]),
    (("expo-location", "geolocation"), ["NSLocationWhenInUseUsageDescription"]),
    (("expo-contacts", "react-native-contacts"), ["NSContactsUsageDescription"]),
    (("expo-calendar",), ["NSCalendarsFullAccessUsageDescription|NSCalendarsUsageDescription"]),
    (("expo-media-library", "cameraroll"),
     ["NSPhotoLibraryUsageDescription|NSPhotoLibraryAddUsageDescription"]),
    (("healthkit", "react-native-health"),
     ["NSHealthShareUsageDescription|NSHealthUpdateUsageDescription"]),
    (("tracking-transparency",), ["NSUserTrackingUsageDescription"]),
    (("local-authentication", "biometrics"), ["NSFaceIDUsageDescription"]),
    (("voice", "speech-recognition"),
     ["NSSpeechRecognitionUsageDescription", "NSMicrophoneUsageDescription"]),
    (("ble-plx", "ble-manager", "bluetooth"), ["NSBluetoothAlwaysUsageDescription"]),
    (("musickit", "apple-music"), ["NSAppleMusicUsageDescription"]),
]
FRAMEWORK_KEYS = {
    "HealthKit": ["NSHealthShareUsageDescription|NSHealthUpdateUsageDescription"],
    "CoreLocation": ["NSLocationWhenInUseUsageDescription|NSLocationAlwaysAndWhenInUseUsageDescription"],
    "AppTrackingTransparency": ["NSUserTrackingUsageDescription"],
    "Contacts": ["NSContactsUsageDescription"],
    "MusicKit": ["NSAppleMusicUsageDescription"],
    "LocalAuthentication": ["NSFaceIDUsageDescription"],
    "Speech": ["NSSpeechRecognitionUsageDescription"],
    "CoreBluetooth": ["NSBluetoothAlwaysUsageDescription"],
    "EventKit": ["NSCalendarsFullAccessUsageDescription|NSCalendarsUsageDescription"],
}
SWIFT_IMPORT_RE = re.compile(
    r"^\s*import\s+(StoreKit|HealthKit|AppTrackingTransparency|AuthenticationServices|"
    r"MusicKit|MediaPlayer|WebKit|SafariServices|GameKit|WeatherKit|UserNotifications|"
    r"CoreLocation|Contacts|ContactsUI|Photos|PhotosUI|AVFoundation|LocalAuthentication|"
    r"CloudKit|ActivityKit|WidgetKit|AppIntents|DeclaredAgeRange|PermissionKit|"
    r"FamilyControls|Speech|CoreBluetooth|EventKit|CoreMotion|AdSupport)\b", re.M)

BACKGROUND_MODE_EVIDENCE = {
    "audio": r"staysActiveInBackground|playsInSilentMode|enableBackgroundPlayback|"
             r"supportsBackgroundPlayback|AVAudioSession|setAudioModeAsync",
    "location": r"startLocationUpdatesAsync|allowsBackgroundLocationUpdates|"
                r"requestAlwaysAuthorization|requestBackgroundPermissionsAsync|"
                r"startMonitoringSignificantLocationChanges",
    "fetch": r"BackgroundFetch|registerTaskAsync|BGAppRefreshTask|setMinimumBackgroundFetchInterval",
    "processing": r"BGProcessingTask|expo-background-task|BackgroundTask\.",
    "remote-notification": r"content-available|contentAvailable|_contentAvailable|"
                           r"enableBackgroundRemoteNotifications|didReceiveRemoteNotification|"
                           r"registerTaskAsync|TaskManager",
    "voip": r"PushKit|PKPushRegistry|CallKit|CXProvider",
    "bluetooth-central": r"CBCentralManager|BleManager|BleManagerModule|react-native-ble",
    "bluetooth-peripheral": r"CBPeripheralManager",
    "external-accessory": r"EAAccessoryManager|ExternalAccessory",
}

SECRET_PATTERNS = [
    ("stripe-live-secret", r"\b(?:sk|rk)_live_[0-9A-Za-z]{10,}"),
    ("stripe-test-secret", r"\bsk_test_[0-9A-Za-z]{10,}"),
    ("private-key-block", r"-----BEGIN (?:EC |RSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    ("anthropic-key", r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    ("openai-key", r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9]{20,}"),
    ("perplexity-key", r"\bpplx-[A-Za-z0-9]{20,}"),
    ("aws-access-key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("github-token", r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    ("slack-token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("expo-public-secret-name", r"\bEXPO_PUBLIC_[A-Z0-9_]*(?:SECRET|PRIVATE|PASSWORD|SERVICE_ROLE)[A-Z0-9_]*"),
]
KEY_FILE_RE = re.compile(r"(\.p8|\.p12|\.pem|\.mobileprovision|service[-_]?account[^/]*\.json)$", re.I)

# group: (scope, pattern, flags, related checks)
LEADS = {
    "external-payment": ("app", r"stripe|paypal|braintree|checkout|billing.?portal|presentPaymentSheet|initPaymentSheet", re.I, "A1"),
    "link-outs": ("app", r"Linking\.openURL\(|openBrowserAsync\(|UIApplication\.shared\.open\(|openURL\(", 0, "A1 D1 D7"),
    "storefront-gating": ("app", r"storefront|Storefront\.current|countryCode|getLocales|regionCode|Locale\.current", re.I, "A1"),
    "hardcoded-prices": ("app", r"[$€£¥] ?\d+[.,]\d{2}\s*(?:/|per |a )?\s*(?:mo|month|yr|year|week|wk)\b", re.I, "A2"),
    "restore-purchases": ("app", r"restorePurchases|restoreTransactions|syncPurchases|getAvailablePurchases|restoreCompletedTransactions|AppStore\.sync", 0, "A3"),
    "trial-eligibility": ("app", r"checkTrialOrIntroductoryPriceEligibility|isEligibleForIntroOffer|introductoryPrice|eligibleIntroOffer", 0, "A4"),
    "subscription-management": ("app", r"showManageSubscriptions|apps\.apple\.com/account/subscriptions|manageSubscriptions", re.I, "A8"),
    "permission-requests": ("app", r"request[A-Za-z]*Permission[A-Za-z]*\(|requestAuthorization\(|requestTrackingAuthorization|requestWhenInUseAuthorization|requestAlwaysAuthorization", 0, "B4"),
    "pre-prompt-buttons": ("app", r">\s*(?:Allow|Not now|Maybe later|Skip|No thanks)\s*<|title=[\"'](?:Allow|Not now|Maybe later|Skip)[\"']", re.I, "B4"),
    "full-photo-access": ("app", r"requestMediaLibraryPermissionsAsync|MediaLibrary\.requestPermissionsAsync|PHPhotoLibrary\.requestAuthorization", 0, "B5"),
    "session-replay": ("app", r"sessionReplay|enableSessionReplay|session_replay|startSessionRecording|FullStory|Smartlook|UXCam|LogRocket", re.I, "B7"),
    "tracking-att": ("app", r"requestTrackingPermissionsAsync|requestTrackingAuthorization|advertisingIdentifier|getAdvertisingId", 0, "C1 C2"),
    "analytics-calls": ("app", r"\.(?:capture|track|logEvent|identify|setUserProperties|setPersonProperties)\(", 0, "C4 G1"),
    "third-party-ai": ("both", r"openai|anthropic|generativelanguage|perplexity|replicate\.com|huggingface|\bgroq\b|mistral\.ai|\bcohere\b|deepseek|bedrock|vertex.?ai|elevenlabs|deepgram|assemblyai", re.I, "C3"),
    "ai-consent": ("app", r"ai.?consent|consent.?ai|third.?party.?ai|ai.?disclos", re.I, "C3"),
    "account-deletion": ("both", r"delete.{0,12}account|deleteAccount|account.{0,12}delet|deactivat|softDelete|deleted_?at|is_?deleted", re.I, "D1"),
    "social-login": ("app", r"GoogleSignin|signInWithGoogle|GIDSignIn|LoginManager|FBSDKLoginKit|signInWithFacebook", 0, "D4"),
    "sign-in-with-apple": ("app", r"AppleAuthentication|appleAuth|signInWithApple|ASAuthorizationAppleIDProvider", 0, "D2 D4 D5"),
    "siwa-token-revocation": ("backend", r"appleid\.apple\.com/auth/(?:revoke|token)|authorization_?code|refresh_token", re.I, "D2"),
    "siwa-relay-domain": ("both", r"privaterelay\.appleid\.com|private\.icloud\.com", re.I, "D3"),
    "ugc-report": ("app", r"report(?:Post|Comment|User|Content|Message|Abuse)|onReport|submitReport|ReportSheet|ReportModal", 0, "E1"),
    "ugc-block": ("app", r"blockUser|unblockUser|blocked(?:Users|Ids)|isBlocked", re.I, "E1"),
    "moderation": ("backend", r"moderat|profan|toxicity|rekognition|perspective.?api|commentanalyzer|nsfw|csam", re.I, "E1 E2"),
    "terms-eula": ("app", r"eula|terms of (?:use|service)|community (?:guidelines|standards)|zero.?tolerance", re.I, "A2 E1"),
    "push-registration": ("app", r"getExpoPushTokenAsync|getDevicePushTokenAsync|registerForRemoteNotifications|OneSignal", 0, "H1"),
    "push-marketing": ("backend", r"marketing|promotional|campaign|newsletter|win.?back|re.?engag|upsell", re.I, "H1"),
    "local-notifications": ("app", r"scheduleNotificationAsync|presentNotificationAsync|UNNotificationRequest|UNUserNotificationCenter\.current\(\)\.add", 0, "H1"),
    "review-prompts": ("app", r"requestReview|StoreReview|SKStoreReviewController|RequestReviewAction|action=write-review|itms-apps://", 0, "H2"),
    "custom-rating-copy": ("app", r"rate (?:us|the app)|enjoy(?:ing)? (?:the|this) app|leave (?:us )?a review|5 stars|five stars", re.I, "H2"),
    "music": ("both", r"MusicKit|apple.?music|MPMusicPlayer|ApplicationMusicPlayer|SystemMusicPlayer|music\.apple\.com|api\.music\.apple\.com|previewUrl", re.I, "H3"),
    "contests": ("app", r"prize|sweepstake|giveaway|raffle|winner|leaderboard|contest", re.I, "H4 F1"),
    "contest-rules": ("app", r"official rules|not (?:a )?sponsor|Apple is not|no purchase necessary", re.I, "H4"),
    "age-signals": ("app", r"DeclaredAgeRange|AgeRangeService|requestAgeRange|PermissionKit|SignificantChange|dateOfBirth|ageGate", re.I, "F4 F5"),
    "healthkit": ("app", r"HealthKit|HKHealthStore|HKQuantityType|queryQuantitySamples|saveQuantitySample|saveWorkout|isHealthDataAvailable", 0, "G1 G2 G4"),
    "icloud": ("app", r"CloudKit|NSUbiquitous|CKContainer", 0, "G2"),
    "hidden-features": ("both", r"review(?:er)?.?mode|isReviewer|appleReview|hideForReview|cupertino|unlock.?code|secret.?menu|easter.?egg", re.I, "I3"),
    "feature-flags": ("app", r"remoteConfig|getFeatureFlag|isFeatureEnabled|useFeatureFlag|featureFlags?", 0, "I3"),
    "debug-ui": ("app", r"Tester|DevMenu|debug(?:Screen|Menu|Panel)|isInternal|isStaff|SkipButton", 0, "I2"),
    "placeholders": ("app", r"lorem ipsum|coming soon|under construction|placeholder text", re.I, "I2"),
    "webview": ("app", r"<WebView|WKWebView|UIWebView|SFSafariViewController", 0, "J1 B9"),
    "webview-bridge": ("app", r"onMessage=|injectedJavaScript|injectJavaScript|addScriptMessageHandler|WKScriptMessageHandler", 0, "J4"),
    "private-api": ("app", r"performSelector|NSClassFromString|dlopen|dlsym", 0, "I5"),
    "dynamic-code": ("app", r"new Function\(|\beval\(", 0, "I5"),
    "ipv4-literals": ("app", r"https?://\d{1,3}(?:\.\d{1,3}){3}", 0, "I8"),
    "other-platforms": ("app", r"Google Play|Play Store|Galaxy Store", 0, "I12"),
    "insecure-token-storage": ("app", r"AsyncStorage\.setItem\(.{0,40}(?:token|jwt|session|password)|UserDefaults.{0,60}(?:token|password)", re.I, "I10"),
}


# ---------------------------------------------------------------- helpers

def load_facts():
    with open(FACTS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def parse_date(value):
    """Accept YYYY-MM-DD or YYYY-MM (treated as the first of the month)."""
    parts = [int(p) for p in str(value).split("-")]
    while len(parts) < 3:
        parts.append(1)
    return dt.date(parts[0], parts[1], parts[2])


def rel(path, base):
    try:
        return str(Path(path).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(path)


def read_text(path):
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", "replace")


def load_plist(path):
    try:
        with open(path, "rb") as fh:
            return plistlib.load(fh)
    except Exception:
        return None


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def is_test_path(path_str):
    p = path_str.replace(os.sep, "/")
    return any(marker in p for marker in TEST_MARKERS)


def mask(secret):
    return secret[:6] + "..." + ("(%d chars)" % len(secret))


def list_files(root):
    """Files the repo exposes: tracked plus untracked-but-not-ignored when in git."""
    root = Path(root).resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
            capture_output=True, check=True, timeout=120)
        names = [n for n in out.stdout.decode("utf-8", "replace").split("\0") if n]
        files = [root / n for n in names]
        files = [f for f in files if not (set(f.relative_to(root).parts) & SKIP_DIRS)]
        return [f for f in files if f.is_file()], True
    except Exception:
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            files.extend(Path(dirpath) / name for name in filenames)
        return files, False


def git_tracked(root, path):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "--", str(path)],
                             capture_output=True, check=True, timeout=60)
        return bool(out.stdout.strip())
    except Exception:
        return None


def dep_names_from_package(pkg):
    deps = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        deps.update(pkg.get(key) or {})
    return deps


def match_groups(names):
    found = {}
    lowered = [n.lower() for n in names]
    for group, needles in SIGNAL_GROUPS.items():
        hits = sorted({n for n in lowered for needle in needles if needle in n})
        if hits:
            found[group] = hits
    return found


# ---------------------------------------------------------------- discovery

def locate(root, files):
    apps, backends = [], []
    for f in files:
        if f.name != "package.json":
            continue
        pkg = load_json(f)
        if not isinstance(pkg, dict):
            continue
        deps = dep_names_from_package(pkg)
        if "expo" in deps or "react-native" in deps:
            apps.append({"root": f.parent, "kind": "expo" if "expo" in deps else "react-native",
                         "package": pkg, "deps": deps})
        elif any(d in deps for d in SERVER_DEPS):
            backends.append(f.parent)
    js_roots = [a["root"] for a in apps]
    native_roots = set()
    for f in files:
        if f.name == "project.pbxproj" and f.parent.suffix == ".xcodeproj":
            proj_dir = f.parent.parent
            if any(proj_dir == r / "ios" or r in proj_dir.parents for r in js_roots):
                continue
            native_roots.add(proj_dir)
    for nr in sorted(native_roots):
        apps.append({"root": nr, "kind": "native", "package": None, "deps": {}})
    for f in files:
        parts = set(f.parts)
        if "android" in parts or "ios" in parts:
            continue
        if f.name in BACKEND_MARKERS or (f.parent.name == "functions" and f.parent.parent.name == "supabase"):
            if any(f.parent == r for r in js_roots):
                continue
            backends.append(f.parent)
    uniq = []
    for b in sorted(set(backends), key=lambda p: len(p.parts)):
        if not any(u == b or u in b.parents for u in uniq):
            uniq.append(b)
    return apps, uniq


# ---------------------------------------------------------------- native config

def resolve_eas_profile(app_root, name="production"):
    eas = load_json(app_root / "eas.json") or {}
    builds = eas.get("build") or {}
    chain, seen, cur = [], set(), name
    while cur and cur in builds and cur not in seen:
        seen.add(cur)
        chain.append(builds[cur])
        cur = builds[cur].get("extends")
    merged = {}
    for prof in reversed(chain):
        for k, v in prof.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v
    return merged if chain else None


def introspect_expo(app_root, profile):
    env = os.environ.copy()
    env["EAS_BUILD_PROFILE"] = "production"
    for k, v in ((profile or {}).get("env") or {}).items():
        env[str(k)] = str(v)
    try:
        out = subprocess.run(["npx", "--no-install", "expo", "config", "--type", "introspect", "--json"],
                             cwd=str(app_root), capture_output=True, timeout=300, env=env)
    except Exception as e:
        return None, "introspection failed to start: %s" % e
    text = out.stdout.decode("utf-8", "replace")
    start = text.find("{")
    if out.returncode != 0 or start < 0:
        return None, "introspection failed: %s" % out.stderr.decode("utf-8", "replace")[-400:]
    try:
        return json.loads(text[start:]), None
    except Exception as e:
        return None, "introspection output was not JSON: %s" % e


def parse_pbxproj(path):
    text = read_text(path) or ""
    info = {}
    for key, val in re.findall(r"INFOPLIST_KEY_(\w+)\s*=\s*\"?(.*?)\"?;\n", text):
        info.setdefault(key, val.replace('\\"', '"'))
    targets = sorted(set(re.findall(r"IPHONEOS_DEPLOYMENT_TARGET\s*=\s*([\d.]+);", text)))
    bundle_ids = sorted(set(re.findall(r"PRODUCT_BUNDLE_IDENTIFIER\s*=\s*\"?([\w.$()-]+)\"?;", text)))
    return {"infoplist_build_settings": info, "deployment_targets": targets,
            "bundle_identifiers": bundle_ids,
            "references_privacy_manifest": "PrivacyInfo.xcprivacy" in text}


def native_files(app_root, files, native_dir):
    plists, ents, manifests, pbx = [], [], [], []
    for f in files:
        if native_dir not in f.parents:
            continue
        s = str(f)
        if is_test_path(s) or ".bundle/" in s or ".appiconset" in s:
            continue
        if f.name == "Info.plist":
            plists.append(f)
        elif f.suffix == ".entitlements":
            ents.append(f)
        elif f.name == "PrivacyInfo.xcprivacy":
            manifests.append(f)
        elif f.name == "project.pbxproj":
            pbx.append(f)
    return plists, ents, manifests, pbx


def podfile_lock_pods(path):
    text = read_text(path) or ""
    block = text.split("DEPENDENCIES:")[0]
    return sorted(set(re.findall(r"^  - \"?([A-Za-z0-9_+./-]+)", block, re.M)))


def spm_packages(path):
    data = load_json(path) or {}
    pins = data.get("pins") or (data.get("object") or {}).get("pins") or []
    return sorted({p.get("identity") or p.get("package") or "" for p in pins} - {""})


# ---------------------------------------------------------------- checks

def classify_purpose(value):
    v = str(value or "").strip()
    low = v.lower()
    issues = []
    if not v:
        return ["empty"]
    if re.search(r"expo dev|dev launcher|development server|metro bundler|packager", low):
        issues.append("development-tool wording")
    if re.search(r"better experience|improve your experience|enhance your experience", low):
        issues.append("vague benefit")
    words = re.findall(r"[a-z0-9$()']+", low)
    request_shape = re.match(r"^(allow|let|please allow|this app|the app|app|we)\b|^\S+( \S+)? (needs|requires|would like)\b", low)
    purpose_markers = (low.count(" to ") >= 2 or
                       re.search(r"\b(so|for|when|because|while|lets you|so that|in order)\b", low))
    if len(words) < 6:
        issues.append("too short to explain the purpose")
    elif request_shape and not purpose_markers:
        issues.append("restates the resource without a purpose")
    return issues


def purpose_report(info_plist, dep_names, frameworks):
    ignored = {"NSUserNotificationsUsageDescription"}  # not read by iOS; some plugins add it
    strings = {k: v for k, v in (info_plist or {}).items()
               if k.endswith("UsageDescription") and k not in ignored}
    evaluated = []
    for key in sorted(strings):
        evaluated.append({"key": key, "value": strings[key], "issues": classify_purpose(strings[key])})
    expected = []
    lowered = [d.lower() for d in dep_names]
    for needles, keys in EXPECTED_KEYS:
        trigger = sorted({d for d in lowered for n in needles if n in d})
        if trigger:
            for k in keys:
                expected.append((k, "dependency " + ", ".join(trigger)))
    for fw in frameworks:
        for k in FRAMEWORK_KEYS.get(fw, []):
            expected.append((k, "import " + fw))
    missing = []
    for k, why in expected:
        options = k.split("|")
        if not any(o in strings for o in options):
            missing.append({"key": k, "because": why,
                            "note": "verify the API is actually called; plugins may add the key at prebuild"})
    return {"strings": evaluated, "possibly_missing": missing}


def aggregate_library_manifests(dirs):
    reasons, owners = {}, {}
    for base in dirs:
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            if "PrivacyInfo.xcprivacy" not in filenames:
                continue
            path = Path(dirpath) / "PrivacyInfo.xcprivacy"
            parts = path.relative_to(base).parts
            pkg = "/".join(parts[:2]) if parts and parts[0].startswith("@") else (parts[0] if parts else "?")
            data = load_plist(path) or {}
            for item in data.get("NSPrivacyAccessedAPITypes", []) or []:
                cat = item.get("NSPrivacyAccessedAPIType")
                if not cat:
                    continue
                reasons.setdefault(cat, set()).update(item.get("NSPrivacyAccessedAPITypeReasons", []) or [])
                owners.setdefault(cat, set()).add(pkg)
    return {c: {"reasons": sorted(reasons[c]), "declared_by": sorted(owners[c])} for c in sorted(reasons)}


def manifest_categories(data):
    cats = {}
    for item in (data or {}).get("NSPrivacyAccessedAPITypes", []) or []:
        cat = item.get("NSPrivacyAccessedAPIType")
        if cat:
            cats.setdefault(cat, set()).update(item.get("NSPrivacyAccessedAPITypeReasons", []) or [])
    return {c: sorted(r) for c, r in cats.items()}


def xcode_from_image(image, sdk, facts):
    eas = facts["eas_ios_images"]
    aliases = eas["sdk_alias_xcode"]
    lowest = min(int(k) for k in aliases)
    if image in (None, "", "auto", "default"):
        if sdk is None:
            return None, "unknown Expo SDK"
        if str(sdk) in aliases:
            return aliases[str(sdk)], "sdk-%s alias (auto)" % sdk
        if sdk < lowest:
            return "%d.x" % eas["below_lowest_alias_xcode_major"], "SDK %s predates the sdk-%d alias" % (sdk, lowest)
        return eas["latest_xcode"], "SDK %s is newer than the known aliases; assuming latest" % sdk
    if image == "latest":
        return eas["latest_xcode"], "latest alias"
    m = re.match(r"sdk-(\d+)$", image)
    if m:
        return aliases.get(m.group(1)), "sdk-%s alias" % m.group(1)
    m = re.search(r"xcode-(\d+(?:\.\d+)?)", image)
    if m:
        return m.group(1), "pinned image %s" % image
    return None, "unrecognized image %s" % image


def xcode_major(version):
    try:
        return int(str(version).split(".")[0])
    except (TypeError, ValueError):
        return None


def dtxcode_to_version(dtx):
    s = str(dtx or "")
    if not s.isdigit() or len(s) < 3:
        return None
    return "%d.%d" % (int(s[:-2]), int(s[-2]))


def version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return None


# ---------------------------------------------------------------- binary

def safe_extract(zip_path, dest):
    dest = Path(dest).resolve()
    with zipfile.ZipFile(zip_path) as z:
        for member in z.infolist():
            if not member.filename.startswith("Payload/"):
                continue
            target = (dest / member.filename).resolve()
            if dest not in target.parents and target != dest:
                continue
            z.extract(member, dest)


def find_app_bundle(base):
    base = Path(base)
    if base.suffix == ".app":
        return base
    for pattern in ("Payload/*.app", "Products/Applications/*.app", "*.app"):
        hits = sorted(base.glob(pattern))
        if hits:
            return hits[0]
    return None


def inspect_binary(path):
    src = Path(path).expanduser()
    tmp = None
    try:
        if src.is_file() and src.suffix.lower() in (".ipa", ".zip"):
            tmp = tempfile.mkdtemp(prefix="basr-binary-")
            safe_extract(src, tmp)
            base = Path(tmp)
        else:
            base = src
        app = find_app_bundle(base)
        if not app:
            return {"source": str(src), "error": "no .app bundle found"}
        info = load_plist(app / "Info.plist") or {}
        result = {
            "source": str(src),
            "bundle_identifier": info.get("CFBundleIdentifier"),
            "display_name": info.get("CFBundleDisplayName") or info.get("CFBundleName"),
            "version": info.get("CFBundleShortVersionString"),
            "build": info.get("CFBundleVersion"),
            "dt_xcode": info.get("DTXcode"),
            "xcode_version": dtxcode_to_version(info.get("DTXcode")),
            "dt_sdk_name": info.get("DTSDKName"),
            "minimum_os": info.get("MinimumOSVersion"),
            "info_plist": info,
            "privacy_manifest": load_plist(app / "PrivacyInfo.xcprivacy"),
            "privacy_bundles": sorted(p.name for p in app.iterdir() if "privacy.bundle" in p.name.lower()),
            "frameworks": sorted(p.name for p in (app / "Frameworks").glob("*")) if (app / "Frameworks").is_dir() else [],
            "extensions": [],
            "uiwebview_references": [],
            "entitlements": None,
        }
        for appex in sorted((app / "PlugIns").glob("*.appex")) if (app / "PlugIns").is_dir() else []:
            ex = load_plist(appex / "Info.plist") or {}
            result["extensions"].append({
                "name": appex.name,
                "point": (ex.get("NSExtension") or {}).get("NSExtensionPointIdentifier"),
                "has_privacy_manifest": (appex / "PrivacyInfo.xcprivacy").is_file()})
        binaries = []
        exe = info.get("CFBundleExecutable")
        if exe:
            binaries.append(app / exe)
        for fw in (app / "Frameworks").glob("*.framework") if (app / "Frameworks").is_dir() else []:
            binaries.append(fw / fw.stem)
        for appex in (app / "PlugIns").glob("*.appex") if (app / "PlugIns").is_dir() else []:
            ex = load_plist(appex / "Info.plist") or {}
            if ex.get("CFBundleExecutable"):
                binaries.append(appex / ex["CFBundleExecutable"])
        for b in binaries:
            try:
                if b.is_file() and b"UIWebView" in b.read_bytes():
                    result["uiwebview_references"].append(rel(b, app))
            except OSError:
                pass
        if shutil.which("codesign"):
            out = subprocess.run(["codesign", "-d", "--entitlements", ":-", str(app)],
                                 capture_output=True, timeout=60)
            raw = out.stdout
            start = raw.find(b"<?xml")
            if start >= 0:
                try:
                    result["entitlements"] = plistlib.loads(raw[start:])
                except Exception:
                    result["entitlements"] = {"raw": raw.decode("utf-8", "replace")[:2000]}
        return result
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- scanning

def scan_leads(file_texts, base, max_hits, scopes):
    leads = {}
    compiled = {g: (scope, re.compile(p, flags), checks) for g, (scope, p, flags, checks) in LEADS.items()}
    for group, (scope, rx, checks) in compiled.items():
        hits, count = [], 0
        for kind, path, text in file_texts:
            if scope != "both" and scope != kind:
                continue
            if kind not in scopes:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    count += 1
                    if len(hits) < max_hits:
                        hits.append({"file": rel(path, base), "line": lineno, "text": line.strip()[:160]})
        if count:
            leads[group] = {"checks": checks, "count": count, "hits": hits}
    return leads


def scan_secrets(paths, base):
    found = []
    compiled = [(name, re.compile(p)) for name, p in SECRET_PATTERNS]
    for path in paths:
        if path.name in LOCKFILES or path.suffix in (".map",) or ".min." in path.name:
            continue
        text = read_text(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, rx in compiled:
                m = rx.search(line)
                if m:
                    found.append({"type": name, "file": rel(path, base), "line": lineno,
                                  "match": mask(m.group(0))})
    for path in paths:
        if KEY_FILE_RE.search(path.name):
            found.append({"type": "key-file-visible-to-git", "file": rel(path, base), "line": 0,
                          "match": path.name})
    return found


def analyze_app(app, repo_root, files, is_git, args, facts, today, binary):
    root = app["root"]
    out = {"root": rel(root, repo_root) or ".", "kind": app["kind"], "notes": []}
    app_files = [f for f in files if root == f.parent or root in f.parents]
    config_text = ""
    deps = sorted(app["deps"])
    native_dir = root if app["kind"] == "native" else root / "ios"

    # native mode
    if app["kind"] == "native":
        out["native_mode"] = "native"
    elif not native_dir.is_dir():
        out["native_mode"] = "cng"
    else:
        tracked = any(native_dir in f.parents for f in app_files) if is_git else None
        if tracked is None:
            out["native_mode"] = "bare (not a git repo; could not confirm ios/ is tracked)"
        else:
            out["native_mode"] = "bare" if tracked else "cng (local ios/ is gitignored and stale)"
    cng = out["native_mode"].startswith("cng")

    # config
    expo_cfg = {}
    if app["kind"] != "native":
        app_json = load_json(root / "app.json") or {}
        expo_cfg = app_json.get("expo", app_json) if isinstance(app_json, dict) else {}
        dynamic = [n for n in ("app.config.js", "app.config.ts", "app.config.mjs", "app.config.cjs") if (root / n).is_file()]
        out["config_files"] = [n for n in ("app.json",) if (root / n).is_file()] + dynamic
        for n in out["config_files"]:
            config_text += read_text(root / n) or ""
        out["expo_sdk"] = None
        ver = (app["deps"] or {}).get("expo")
        if ver:
            m = re.search(r"(\d+)", str(ver))
            out["expo_sdk"] = int(m.group(1)) if m else None
        out["react_native"] = (app["deps"] or {}).get("react-native")

    profile = resolve_eas_profile(root) if app["kind"] != "native" else None
    out["eas_production_profile"] = profile

    info_plist, entitlements, app_manifest, truth = {}, {}, None, None
    if cng:
        if args.introspect and app["kind"] == "expo":
            cfg, err = introspect_expo(root, profile)
            if cfg:
                ios = cfg.get("ios") or {}
                info_plist = ios.get("infoPlist") or {}
                entitlements = ios.get("entitlements") or {}
                app_manifest = ios.get("privacyManifests")
                truth = "expo introspection (production profile env)"
                out["bundle_identifier"] = ios.get("bundleIdentifier")
                out["supports_tablet"] = ios.get("supportsTablet")
                if cfg.get("sdkVersion"):
                    out["expo_sdk"] = xcode_major(cfg["sdkVersion"])
                out["plugins"] = [p if isinstance(p, str) else p[0] for p in cfg.get("plugins") or []]
            else:
                out["notes"].append(err)
        if truth is None:
            ios = expo_cfg.get("ios") or {}
            info_plist = ios.get("infoPlist") or {}
            entitlements = ios.get("entitlements") or {}
            app_manifest = ios.get("privacyManifests")
            out["bundle_identifier"] = ios.get("bundleIdentifier")
            out["supports_tablet"] = ios.get("supportsTablet")
            truth = "static app.json only (plugin-injected values missing; rerun with --introspect or --ipa)"
    else:
        plists, ents, manifests, pbx = native_files(root, app_files, native_dir)
        out["info_plists"] = [rel(p, repo_root) for p in plists]
        for p in plists:
            data = load_plist(p) or {}
            if "NSExtension" in data:
                continue
            if "CFBundleExecutable" in data or "UIApplicationSceneManifest" in data or not info_plist:
                for k, v in data.items():
                    info_plist.setdefault(k, v)
        pbx_info = [parse_pbxproj(p) for p in pbx]
        for info in pbx_info:
            for k, v in info["infoplist_build_settings"].items():
                info_plist.setdefault(k, v)
        out["xcode_projects"] = [dict(file=rel(p, repo_root), **parse_pbxproj(p)) for p in pbx]
        for e in ents:
            entitlements.update(load_plist(e) or {})
        out["entitlement_files"] = [rel(e, repo_root) for e in ents]
        app_manifests = [m for m in manifests if "Pods" not in m.parts]
        out["app_privacy_manifests"] = [rel(m, repo_root) for m in app_manifests]
        if app_manifests:
            app_manifest = {"NSPrivacyAccessedAPITypes": []}
            for m in app_manifests:
                app_manifest["NSPrivacyAccessedAPITypes"] += (load_plist(m) or {}).get("NSPrivacyAccessedAPITypes", [])
        truth = "native project files"
        lock = native_dir / "Podfile.lock"
        if lock.is_file():
            deps += podfile_lock_pods(lock)
        for f in app_files:
            if f.name == "Package.resolved":
                deps += spm_packages(f)

    if binary and binary.get("info_plist"):
        out["binary_matches_app"] = (binary.get("bundle_identifier") == out.get("bundle_identifier")
                                     if out.get("bundle_identifier") else None)
    if out.get("binary_matches_app") is False:
        out["notes"].append("binary %s does not match app bundle id %s; ignored as production evidence"
                            % (binary.get("bundle_identifier"), out.get("bundle_identifier")))
    out["native_truth_source"] = truth
    out["dependencies"] = sorted(set(deps))
    out["signals"] = match_groups(deps)

    # Swift / Objective-C framework imports
    frameworks = set()
    texts = []
    for f in app_files:
        if f.suffix not in APP_EXT or is_test_path(str(f)):
            continue
        if cng and native_dir in f.parents:
            continue
        t = read_text(f)
        if t is None:
            continue
        texts.append(("app", f, t))
        if f.suffix in (".swift", ".m", ".mm", ".h"):
            frameworks.update(SWIFT_IMPORT_RE.findall(t))
    out["frameworks_imported"] = sorted(frameworks)

    effective_plist = dict(info_plist)
    if binary and binary.get("info_plist") and out.get("binary_matches_app") is not False:
        for k, v in binary["info_plist"].items():
            effective_plist.setdefault(k, v)
    out["purpose_strings"] = purpose_report(effective_plist, deps, frameworks)
    if truth.startswith("static") and any(n.startswith("app.config") for n in out.get("config_files", [])) \
            and not (binary and binary.get("info_plist")):
        out["purpose_strings"]["possibly_missing"] = []
        out["notes"].append("dynamic app config without --introspect or --ipa: purpose strings are incomplete, "
                            "missing-key detection skipped")
    out["entitlements"] = entitlements or (binary or {}).get("entitlements")
    out["info_plist_flags"] = {k: effective_plist.get(k) for k in (
        "UIBackgroundModes", "ITSAppUsesNonExemptEncryption", "NSAppTransportSecurity",
        "UIRequiredDeviceCapabilities", "LSApplicationQueriesSchemes", "UIApplicationSceneManifest")
        if k in effective_plist}

    # background modes
    modes = effective_plist.get("UIBackgroundModes") or []
    joined = "\n".join(t for _, _, t in texts) + "\n" + config_text
    bg = []
    for mode in modes:
        rx = BACKGROUND_MODE_EVIDENCE.get(mode)
        evidence = bool(rx and re.search(rx, joined))
        bg.append({"mode": mode, "code_evidence_found": evidence if rx else None})
    out["background_modes"] = bg

    # privacy manifests
    lib_dirs = [root / "node_modules"] if app["kind"] != "native" else [native_dir / "Pods", root / "Pods"]
    library = aggregate_library_manifests(lib_dirs)
    app_level = manifest_categories(app_manifest) if app_manifest else None
    app_level_source = truth if app_manifest else None
    if binary and binary.get("privacy_manifest") and out.get("binary_matches_app") is not False:
        app_level = manifest_categories(binary["privacy_manifest"])
        app_level_source = "built binary"
    gaps = None
    if app_level is not None:
        gaps = [c for c in library if c not in app_level]
    out["privacy_manifest"] = {
        "library_union": library,
        "app_level": app_level,
        "app_level_source": app_level_source,
        "categories_missing_at_app_level": gaps,
        "note": None if app_level is not None else (
            ("app-level manifest not visible: Expo writes a default at prebuild; "
             + ("the supplied binary is a different variant, pass a production build"
                if out.get("binary_matches_app") is False else "pass --ipa to confirm"))
            if cng else "no app-level PrivacyInfo.xcprivacy found"),
    }

    # toolchain
    tool = {"evidence": None, "xcode": None, "blocking": [], "warnings": []}
    if binary and binary.get("xcode_version") and out.get("binary_matches_app") is not False:
        tool["xcode"], tool["evidence"] = binary["xcode_version"], "built binary DTXcode %s, %s" % (
            binary.get("dt_xcode"), binary.get("dt_sdk_name"))
    elif app["kind"] != "native":
        image = ((profile or {}).get("ios") or {}).get("image") or facts["eas_ios_images"]["default_image"]
        xcode, why = xcode_from_image(image, out.get("expo_sdk"), facts)
        tool["xcode"], tool["evidence"] = xcode, "eas.json production ios.image=%s (%s)" % (image, why)
        tool["image"] = image
    else:
        tool["evidence"] = "native project: read the CI Xcode selection or pass --ipa"
    major = xcode_major(tool["xcode"])
    reqs = sorted(facts["upload_requirements"], key=lambda r: parse_date(r["effective"]))
    current = [r for r in reqs if parse_date(r["effective"]) <= today]
    upcoming = [r for r in reqs if parse_date(r["effective"]) > today]
    if major is not None and current and major < current[-1]["min_xcode_major"]:
        tool["blocking"].append("Xcode %s is below the current upload minimum (%s since %s)" % (
            tool["xcode"], current[-1]["summary"], current[-1]["effective"]))
    if major is not None and upcoming and major < upcoming[0]["min_xcode_major"]:
        tool["warnings"].append("Xcode %s will be below the upload minimum from %s (%s)" % (
            tool["xcode"], upcoming[0]["effective"], upcoming[0]["summary"]))
    scene = facts["eas_ios_images"]["scene_lifecycle"]
    sdk = out.get("expo_sdk")
    if (app["kind"] == "expo" and major is not None and sdk is not None
            and major >= scene["required_from_xcode_major"] and sdk < scene["native_from_sdk"]):
        flagged = sdk == scene["flag_sdk"] and "enableSceneSupport" in config_text
        if not flagged:
            tool["blocking"].append("Xcode %s build on Expo SDK %s without UIKit scene life cycle: %s" % (
                tool["xcode"], sdk, scene["rule"]))
    min_target = facts["min_deployment_target"]
    targets = []
    if binary and binary.get("minimum_os"):
        targets.append(binary["minimum_os"])
    for proj in out.get("xcode_projects", []):
        targets += proj["deployment_targets"]
    if targets and parse_date(min_target["effective"]) <= today:
        low = [t for t in targets if (version_tuple(t) or (99,)) < version_tuple(min_target["ios"])]
        if low:
            tool["blocking"].append("deployment target %s is below iOS %s (required since %s)" % (
                ", ".join(sorted(set(low))), min_target["ios"], min_target["effective"]))
    out["toolchain"] = tool

    out["_texts"] = texts
    return out


def collect_backend_texts(backends, files):
    texts = []
    for f in files:
        if f.suffix not in BACKEND_EXT or is_test_path(str(f)):
            continue
        if any(b == f.parent or b in f.parents for b in backends):
            t = read_text(f)
            if t is not None:
                texts.append(("backend", f, t))
    return texts


def run(args):
    facts = load_facts()
    today = parse_date(args.today) if args.today else dt.date.today()
    repo_root = Path(args.path).resolve()
    if not repo_root.is_dir():
        print("not a directory: %s" % repo_root, file=sys.stderr)
        return None
    files, is_git = list_files(repo_root)
    apps, backends = locate(repo_root, files)
    binary = inspect_binary(args.ipa) if args.ipa else None

    report = {
        "schema": SCHEMA,
        "tool_version": TOOL_VERSION,
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "today": today.isoformat(),
        "facts_baseline": facts["baseline"],
        "root": str(repo_root),
        "git_repo": is_git,
        "backends": [rel(b, repo_root) for b in backends],
        "apps": [],
        "binary": None,
        "secrets": [],
        "blocking_signals": [],
        "upcoming_deadlines": [d for d in facts["deadlines"] if parse_date(d["date"]) >= dt.date(today.year, today.month, 1)],
    }
    if binary:
        report["binary"] = {k: v for k, v in binary.items() if k != "info_plist"}
        if binary.get("uiwebview_references"):
            report["blocking_signals"].append({
                "id": "uiwebview-in-binary", "checks": "I6",
                "message": "UIWebView referenced in shipped binaries (ITMS-90809); confirm with Apple's upload result",
                "evidence": binary["uiwebview_references"]})

    backend_texts = collect_backend_texts(backends, files)
    for app in apps:
        a = analyze_app(app, repo_root, files, is_git, args, facts, today, binary)
        texts = a.pop("_texts")
        a["leads"] = scan_leads(texts + backend_texts, repo_root, args.max_hits, {"app", "backend"})
        for msg in a["toolchain"]["blocking"]:
            evidence = ("IPHONEOS_DEPLOYMENT_TARGET or MinimumOSVersion" if msg.startswith("deployment target")
                        else a["toolchain"]["evidence"])
            report["blocking_signals"].append({"id": "toolchain", "checks": "I1", "app": a["root"],
                                               "message": msg, "evidence": evidence})
        report["apps"].append(a)
    if not apps:
        report["notes"] = ["no Expo, React Native, or Xcode project found under this path"]

    scan_paths = [f for f in files if f.suffix in APP_EXT | BACKEND_EXT | {".json", ".plist", ".yml", ".yaml", ".env", ".xcconfig", ".properties", ".toml"}
                  or f.name.startswith(".env") or KEY_FILE_RE.search(f.name)]
    report["secrets"] = scan_secrets(scan_paths, repo_root)
    serious = [s for s in report["secrets"] if s["type"] not in ("stripe-test-secret",)]
    if serious:
        report["blocking_signals"].append({
            "id": "server-secrets", "checks": "I10",
            "message": "possible server-side secrets or key files visible to git; read each hit (publishable keys are not findings)",
            "evidence": ["%s:%s %s" % (s["file"], s["line"], s["type"]) for s in serious[:20]]})
    return report


# ---------------------------------------------------------------- output

def to_markdown(r):
    lines = ["# App Store pre-scan", "",
             "Tool %s, facts baseline: guidelines last updated %s (verified %s). Scan date %s." % (
                 r["tool_version"], r["facts_baseline"]["guidelines_last_updated"],
                 r["facts_baseline"]["verified_on"], r["today"]),
             "", "Leads, not findings: read the code before reporting anything.", ""]
    lines.append("## Blocking signals")
    if r["blocking_signals"]:
        for s in r["blocking_signals"]:
            ev = s.get("evidence")
            ev = "; ".join(ev) if isinstance(ev, list) else ev
            lines.append("- [%s] %s (%s)" % (s["checks"], s["message"], ev))
    else:
        lines.append("- None")
    if r.get("binary"):
        b = r["binary"]
        lines += ["", "## Binary", "- %s %s (%s), Xcode %s, SDK %s, minimum iOS %s" % (
            b.get("bundle_identifier"), b.get("version"), b.get("build"), b.get("xcode_version"),
            b.get("dt_sdk_name"), b.get("minimum_os"))]
    lines += ["", "## Backends", "- " + (", ".join(r["backends"]) if r["backends"] else "none in repo")]
    for a in r["apps"]:
        lines += ["", "## App: %s (%s, %s)" % (a["root"], a["kind"], a["native_mode"]),
                  "- Native truth: %s" % a["native_truth_source"]]
        if a.get("expo_sdk"):
            lines.append("- Expo SDK %s, React Native %s" % (a["expo_sdk"], a.get("react_native")))
        t = a["toolchain"]
        lines.append("- Toolchain: Xcode %s via %s" % (t.get("xcode"), t.get("evidence")))
        for w in t["warnings"]:
            lines.append("  - warning: %s" % w)
        for n in a["notes"]:
            lines.append("- note: %s" % n)
        if a["signals"]:
            lines.append("- Signals: " + "; ".join("%s (%s)" % (g, ", ".join(v[:4])) for g, v in a["signals"].items()))
        ps = a["purpose_strings"]
        flagged = [s for s in ps["strings"] if s["issues"]]
        lines.append("- Purpose strings: %d found, %d flagged, %d possibly missing" % (
            len(ps["strings"]), len(flagged), len(ps["possibly_missing"])))
        for s in flagged:
            lines.append("  - %s: %s (\"%s\")" % (s["key"], ", ".join(s["issues"]), str(s["value"])[:90]))
        for m in ps["possibly_missing"]:
            lines.append("  - possibly missing %s (%s)" % (m["key"], m["because"]))
        for bg in a["background_modes"]:
            if bg["code_evidence_found"] is False:
                lines.append("- Background mode `%s` has no matching code found" % bg["mode"])
        pm = a["privacy_manifest"]
        if pm["categories_missing_at_app_level"]:
            lines.append("- Privacy manifest: library categories missing at app level: %s" % ", ".join(pm["categories_missing_at_app_level"]))
        elif pm["note"]:
            lines.append("- Privacy manifest: %s" % pm["note"])
        lines.append("- Leads by group (count, related checks):")
        for g, v in sorted(a["leads"].items()):
            example = " e.g. %s:%s" % (v["hits"][0]["file"], v["hits"][0]["line"]) if v["hits"] else ""
            lines.append("  - %s: %d [%s]%s" % (g, v["count"], v["checks"], example))
    lines += ["", "## Secrets (masked)"]
    lines += ["- %s:%s %s %s" % (s["file"], s["line"], s["type"], s["match"]) for s in r["secrets"]] or ["- None"]
    lines += ["", "## Upcoming deadlines"]
    lines += ["- %s: %s [%s]" % (d["date"], d["item"], ", ".join(d["checks"])) for d in r["upcoming_deadlines"]] or ["- None"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only App Store readiness pre-scan.")
    p.add_argument("path", nargs="?", default=".", help="project or repository root (default: .)")
    p.add_argument("--introspect", action="store_true",
                   help="evaluate Expo config with `npx --no-install expo config --type introspect` (runs project config code, writes nothing)")
    p.add_argument("--ipa", metavar="PATH", help="built .ipa, .xcarchive, or .app to inspect")
    p.add_argument("--format", choices=("json", "md"), default="json")
    p.add_argument("--out", metavar="FILE", help="write output here instead of stdout")
    p.add_argument("--fail-on", choices=("blocker", "never"), default="never",
                   help="exit 1 when blocking signals exist (for CI)")
    p.add_argument("--max-hits", type=int, default=25, help="lead hits kept per group (default 25)")
    p.add_argument("--today", metavar="YYYY-MM-DD", help="evaluate dated requirements as of this date")
    args = p.parse_args(argv)
    try:
        report = run(args)
    except FileNotFoundError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    if report is None:
        return 2
    text = to_markdown(report) if args.format == "md" else json.dumps(report, indent=1, default=str) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.fail_on == "blocker" and report["blocking_signals"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
