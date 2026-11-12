# Detection recipes

Conventions:
- Run from the app root (`$APP`, found in "locate") unless a recipe is marked [backend],
  which means: run it against each backend directory found in "locate".
- `$SCRATCH` is your scratch directory (the harness scratchpad, or `mktemp -d`). Never write
  inside the repo.
- ripgrep honors `.gitignore`, which already skips `node_modules`, `Pods`, build output and,
  in CNG projects, the stale `ios/` directory. Add `--no-ignore` only when you mean to search
  `node_modules`.
- `-t ts -t js` covers .ts, .tsx, .js, .jsx, .mjs, .cjs.
- Every rg command passes an explicit path (`.`, `"$BACKEND"`, `"$APPDIR"`). Without one,
  rg searches stdin whenever stdin is a pipe and silently reports nothing, which reads as
  "no violation". Keep the path when adapting a recipe.
- Every hit is a lead, not a finding. Read the file with context before reporting.
- Native Swift or Objective-C projects: see "native-swift" for the equivalent patterns.

## scanner (run first)

```sh
python3 "<skill>/scripts/scan.py" "$ROOT" --introspect --format json --out "$SCRATCH/scan.json"
python3 "<skill>/scripts/scan.py" "$ROOT" --introspect --format md
```

Add `--ipa <production .ipa, .xcarchive, or .app>` when a production build is available.
Drop `--introspect` if the user does not want the app config evaluated (it runs project
config code but writes nothing). The scanner is read-only, uses only the Python standard
library, and covers locate, native-mode, native-config, binary, signal-deps, toolchain,
privacy-manifest, background modes, and secrets, plus grouped leads (with related check IDs)
for every other recipe below. Use the recipes to confirm and go deeper, and as the fallback
when python3 is unavailable.

## locate

```sh
# App roots: package.json files that depend on expo or react-native
rg -l -g '**/package.json' -g '!**/node_modules/**' '"(expo|react-native)"\s*:' .
# Backend candidates in the same repository
rg --files -g '!**/node_modules/**' -g 'pom.xml' -g 'build.gradle*' -g 'go.mod' -g 'pyproject.toml' -g 'requirements.txt' -g 'Gemfile' -g 'composer.json' -g 'firebase.json' -g 'serverless.yml' . | head -20
rg -l -g '**/package.json' -g '!**/node_modules/**' '"(express|fastify|@nestjs/core|koa|hono)"\s*:' .
ls -d supabase/functions functions api server backend 2>/dev/null
```

Interpretation: in a monorepo the app root is not the repo root; pass both to auditors. When
a backend is present, auditors follow data flows into it (deletion, moderation, push,
AI, Sign in with Apple revocation). When it is absent, those checks become needs-user.

## native-mode

```sh
git ls-files ios | head -3
git check-ignore -q ios && echo "ios/ is gitignored: CNG project"
ls app.json app.config.js app.config.ts 2>/dev/null
rg -n '"expo"\s*:|"react-native"\s*:' package.json
```

Interpretation:
- **CNG (Continuous Native Generation):** `ios/` is untracked or gitignored. EAS runs prebuild
  from the app config, so a local `ios/` directory is a stale artifact and is NOT evidence.
  Use "native-config" (introspection) as ground truth.
- **Bare:** `ios/` is tracked. Its `Info.plist`, entitlements, and `PrivacyInfo.xcprivacy`
  are ground truth; app.json values may be ignored.
- **Native:** a `.xcodeproj` with no React Native or Expo package.json. Read the target's
  Info.plist, `INFOPLIST_KEY_*` build settings in `project.pbxproj` (Xcode-generated
  Info.plist), entitlements, and `PrivacyInfo.xcprivacy`; see "native-swift".
- **Dynamic config** (`app.config.js` or `.ts`): values can depend on env (`APP_VARIANT`,
  `EAS_BUILD_PROFILE`, others). Read `eas.json` `build.production` (and any profile it
  `extends`) and evaluate config with those env values.

## native-config

CNG ground truth (read-only; evaluates config plugins and mods without writing native files;
needs `node_modules` installed):

```sh
EAS_BUILD_PROFILE=production npx expo config --type introspect --json > "$SCRATCH/introspect.json"
python3 -I - "$SCRATCH/introspect.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1])); ios = c.get("ios", {}); p = ios.get("infoPlist", {})
print("sdkVersion:", c.get("sdkVersion"), "bundleIdentifier:", ios.get("bundleIdentifier"),
      "supportsTablet:", ios.get("supportsTablet"), "usesAppleSignIn:", ios.get("usesAppleSignIn"))
keys = ("UIBackgroundModes", "ITSAppUsesNonExemptEncryption", "NSAppTransportSecurity",
        "LSApplicationQueriesSchemes", "UIRequiredDeviceCapabilities", "UIApplicationSceneManifest")
for k in sorted(p):
    if k.endswith("UsageDescription") or k in keys:
        print(f"{k} = {p[k]}")
print("entitlements:", json.dumps(ios.get("entitlements", {}), indent=1))
print("privacyManifests:", json.dumps(ios.get("privacyManifests"), indent=1))
print("plugins:", [x if isinstance(x, str) else x[0] for x in c.get("plugins", [])])
PY
```

Add any other `build.production.env` values from eas.json to the command if the config reads
them. If introspection fails, fall back to the app config plus each config plugin's defaults
(read `node_modules/<pkg>/app.plugin.js` and its `plugin/build` source).

Bare ground truth:

```sh
plutil -p ios/*/Info.plist | rg 'UsageDescription|UIBackgroundModes|ITSApp|NSAppTransportSecurity|LSApplicationQueriesSchemes|UIRequiredDeviceCapabilities|UIApplicationSceneManifest' -A 3
cat ios/*/*.entitlements
```

Interpretation:
- Purpose strings starting "Allow $(PRODUCT_NAME) to access your ..." with nothing more are
  plugin defaults that restate the resource (B2). Strings naming development tools ("Expo Dev
  Launcher ... development servers") come from dev-client plugins; confirm in a production
  IPA whether they ship.
- Every permission-bearing native library predicts a usage key; a referenced API with no key
  fails upload (ITMS-90683).
- `UIBackgroundModes` often comes from plugin options, not app.json (I7).
- Entitlements drive G4 (HealthKit), D4 (`com.apple.developer.applesignin`), H1
  (`aps-environment`), G2 (iCloud).

## binary (optional, strongest evidence of what shipped)

```sh
ls -t *.ipa build/*.ipa dist/*.ipa 2>/dev/null | head -1
mkdir -p "$SCRATCH/ipa" && cp "<path-to.ipa>" "$SCRATCH/ipa/app.ipa" && unzip -o -q "$SCRATCH/ipa/app.ipa" -d "$SCRATCH/ipa"
APPDIR=$(ls -d "$SCRATCH"/ipa/Payload/*.app)
plutil -p "$APPDIR/Info.plist" | rg 'CFBundleIdentifier|CFBundleDisplayName|CFBundleShortVersionString|CFBundleVersion"|DTSDKName|DTXcode"|MinimumOSVersion|UsageDescription|UIBackgroundModes|ITSApp'
plutil -p "$APPDIR/PrivacyInfo.xcprivacy"
codesign -d --entitlements :- "$APPDIR" 2>/dev/null
ls "$APPDIR/Frameworks" "$APPDIR" | rg -i 'privacy|framework'
rg -a -l 'UIWebView' "$APPDIR" | head
```

Interpretation: first confirm `CFBundleIdentifier` and `CFBundleDisplayName` match the
production app; development or preview variants use other identifiers and names and are not
evidence for production. Record the version and build number: the IPA may predate HEAD.
`DTSDKName` (for example `iphoneos26.5`) and `DTXcode` (four digits: `2620` is Xcode 26.2)
prove the toolchain for I1.

## signal-deps

```sh
rg -n 'iap|purchases|superwall|adapty|qonversion|stripe|paypal|braintree|payments' package.json
rg -n 'tracking-transparency|fbsdk|facebook|appsflyer|adjust|branch|singular|kochava|tiktok|snapchat|google-mobile-ads|admob|applovin|ironsource|unity-ads|vungle|chartboost|inmobi|firebase/analytics' package.json
rg -n 'posthog|amplitude|mixpanel|segment|rudderstack|sentry|bugsnag|datadog|instabug|logrocket|fullstory|smartlook|uxcam|clarity|heap' package.json
rg -n 'openai|anthropic|generative-ai|google/genai|perplexity|replicate|huggingface|groq|mistral|cohere|deepseek|together|@ai-sdk|langchain|elevenlabs|deepgram|assemblyai|stability' package.json
rg -n 'health|pedometer|sensors|motion' package.json
rg -n 'google-signin|fbsdk|auth-session|web-browser|apple-authentication|app-auth|clerk|auth0|firebase/auth|supabase|local-authentication|biometrics' package.json
rg -n 'location|geolocation|camera|contacts|calendar|media-library|image-picker|document-picker|expo-av|expo-audio|expo-video|voice|speech|ble|bluetooth|nfc|permissions' package.json
rg -n 'notifications|messaging|onesignal|notifee|push|store-review|rate|in-app-review|music|game-center|gamekit|weather|live-activit|widget|apple-targets|siri|intents' package.json
rg -n 'webview|web-browser' package.json
rg -n 'expo-updates|code-push|codepush|revopush|hot-updater|remote-config|launchdarkly|statsig|growthbook|configcat|flagsmith|unleash' package.json
ls modules targets 2>/dev/null
```

What each group implies:
- Payments: domain A. No IAP library while digital goods are sold is itself a lead for A1.
- Tracking, ads, attribution: C1, C2, C6. Deep-linking SDKs (Branch, AppsFlyer OneLink)
  count as tracking when they create cross-company identity.
- Product analytics and replay: C4 payloads, B7 replay, B3 manifests.
- AI: C3 (also search the backend, where most AI calls live).
- Health and motion: domain G.
- Accounts: domain D.
- Permission libraries: B2, B4, B5.
- Engagement: H1 push, H2 review prompts, H3 music, H5 Game Center, H6 widgets.
- WebView: J1, J4, B9.
- OTA and flags: I3, I4.
- `modules/` (local Expo modules) and `targets/` (widgets, extensions): read their Swift for
  MusicKit, DeclaredAgeRange, HealthKit, and extension ads.

## environment

```sh
rg -n 'localhost|127\.0\.0\.1|192\.168\.|10\.0\.2\.2|staging|ngrok|\.local:' -t ts -t js -t json .
rg -n 'API_URL|BASE_URL|baseURL|apiUrl' -t ts -t js . | head -30
cat eas.json 2>/dev/null
```

Interpretation: a localhost or staging default matters only if the production build
resolves to it. Trace eas.json env, `__DEV__` guards, and env-file handling.

## external-payment

```sh
rg -n 'stripe|paypal|braintree|checkout|billing.?portal|paymentsheet|presentPaymentSheet|initPaymentSheet' -i -t ts -t js .
rg -n '(openURL|openBrowserAsync|openAuthSessionAsync)\(' -t ts -t js .
rg -n 'license.?key|unlock.?code|promo.?code|redeem|coupon|boost' -i -t ts -t js .
```

Interpretation: read 20 lines around each link-out. Decide from what is sold (A1 scoped
cases), not from the dependency.

## storefront

```sh
rg -n 'storefront|getStorefront|Storefront\.current|countryCode' -i -t ts -t js .
rg -n 'getLocales|Localization\.(region|locale)|regionCode|timeZone|ipapi|geoip|ip-api' -i -t ts -t js .
```

Interpretation: purchase link-outs gated by the second list (locale, region, timezone, IP)
instead of the StoreKit storefront are an A1 finding.

## paywall

```sh
rg -l 'paywall|subscribe|subscription|premium|upgrade|getOfferings|purchasePackage|requestPurchase|RevenueCatUI|Superwall' -i -t ts -t js .
rg -n '[$€£¥] ?[0-9]+([.,][0-9]{2})?' -t ts -t js . | rg -i 'month|year|week|annual|trial|price|/mo|/yr'
rg -n 'priceString|localizedPriceString|displayPrice|localizedPrice|pricePerMonth|pricePerWeek|introPrice|introductoryPrice' -t ts -t js .
rg -n 'terms|eula|privacy' -i -t ts -t js -l .
```

Interpretation: the second command finds hardcoded prices (A2). Per-period breakdown fields
(`pricePerWeek`) rendered larger than the billed price are an A2 finding.

## permission-flows

```sh
rg -n 'request[A-Za-z]*Permission[A-Za-z]*\(|requestTrackingPermissionsAsync|requestAuthorization\(' -t ts -t js .
rg -n '>\s*(Allow|Not now|Maybe later|Skip|No thanks)\s*<|title=["\x27](Allow|Not now|Maybe later|Skip)' -i -t ts -t js .
```

Interpretation: for each request, read the preceding screen (B4 pre-alert rules) and the
denial branch.

## recording

```sh
rg -n 'sessionReplay|enableSessionReplay|session_replay|startSessionRecording|FullStory|Smartlook|UXCam|LogRocket|Clarity|recordScreen' -i -t ts -t js .
rg -n 'PostHog(Provider)?' -A 20 -t ts -t js . | rg -i 'replay|record|mask'
rg -n 'startRecording|recordAsync|useAudioRecorder|prepareToRecordAsync|Audio\.Recording|startRecordingAsync' -t ts -t js .
```

## privacy-manifest

```sh
python3 -I - node_modules <<'PY'
import os, sys, plistlib, collections
reasons = collections.defaultdict(set); owners = collections.defaultdict(set)
for root, dirs, files in os.walk(sys.argv[1]):
    if "PrivacyInfo.xcprivacy" not in files:
        continue
    path = os.path.join(root, "PrivacyInfo.xcprivacy")
    rel = path.split("node_modules/")[-1].split("/")
    pkg = "/".join(rel[:2]) if rel[0].startswith("@") else rel[0]
    try:
        data = plistlib.load(open(path, "rb"))
    except Exception as e:
        print("unreadable:", path, e); continue
    for t in data.get("NSPrivacyAccessedAPITypes", []):
        cat = t.get("NSPrivacyAccessedAPIType")
        reasons[cat].update(t.get("NSPrivacyAccessedAPITypeReasons", []))
        owners[cat].add(pkg)
for cat in sorted(reasons):
    print(cat, sorted(reasons[cat]), "declared by", sorted(owners[cat]))
PY
rg -n 'PrivacyInfo.xcprivacy' ios/*.xcodeproj/project.pbxproj 2>/dev/null
```

Interpretation: compare the union above with the app-level manifest (CNG:
`privacyManifests` in introspection plus template defaults visible in a built IPA; bare:
`ios/<App>/PrivacyInfo.xcprivacy` and its target membership). Any category with no app-level
reason is a B3 lead. For Apple's listed SDKs, confirm versions that ship manifests (IPA:
`<SDK>_Privacy.bundle` in the app).

## analytics-payloads

```sh
rg -n '\.(capture|track|logEvent|identify|screen|setUserProperties|setPersonProperties|register|people\.set)\(' -t ts -t js .
```
[backend] same calls for server-side analytics SDKs.

Interpretation: read each call and list properties. Health values, photos, precise location,
contacts, and message text in third-party analytics are C4 and G1 leads.

## third-party-ai

```sh
rg -n -i 'openai|anthropic|claude|gemini|generativelanguage|perplexity|replicate|huggingface|groq|mistral|cohere|deepseek|together\.ai|bedrock|vertex.?ai|azure.?openai|elevenlabs|deepgram|assemblyai|stability\.ai' -t ts -t js .
rg -n 'api\.openai\.com|api\.anthropic\.com|api\.perplexity\.ai|generativelanguage\.googleapis\.com|api\.mistral\.ai|api\.groq\.com|api\.replicate\.com' -t ts -t js -t json -t yaml .
rg -n -i 'ai.?consent|consent.?ai|third.?party.?ai|ai.?disclos|accepted.?ai|ai.?opt' -t ts -t js .
```
[backend] the first two patterns with `-t java -t kotlin -t py -t go -t ts -t js -t ruby -t php -t yaml`.

Interpretation: trace each provider call back to the user action that triggers it and the
data it carries, then find the consent surface that precedes the first call (C3).

## accounts

```sh
rg -n 'delete.{0,12}account|deleteAccount|account.{0,12}delet|deactivat|closeAccount' -i -t ts -t js .
rg -n 'GoogleSignin|signInWithGoogle|LoginManager|AppleAuthentication|appleAuth|signInWithApple|AuthSession|useAuthRequest' -t ts -t js .
rg -n 'privaterelay\.appleid\.com|private\.icloud\.com|disposable|isDisposable|(allow|block|deny).?list' -i -t ts -t js .
```
[backend]
```sh
rg -n -i 'deleteAccount|delete.{0,20}user|softDelete|deleted_?at|is_?deleted|is_?active|deactivat' "$BACKEND"
rg -n 'appleid\.apple\.com/auth/(revoke|token)|authorizationCode|authorization_code|refresh_token' "$BACKEND"
rg -n 'privaterelay\.appleid\.com|private\.icloud\.com|disposable' "$BACKEND"
```

Interpretation: follow the delete button to the endpoint and read what it removes (rows,
media objects, UGC). Soft-delete flags alone fail D1.

## ugc

```sh
rg -l 'comment|post|reply|chat|message|feed|caption|bio|profile|review' -i -t ts -t js . | head -40
rg -n 'report|flag' -i -t ts -t js -l .
rg -n 'blockUser|block(ed)?Users?|unblock' -i -t ts -t js -l .
rg -n 'eula|terms of (use|service)|community (guidelines|standards)|zero.?tolerance' -i -t ts -t js .
```
[backend]
```sh
rg -l -i 'moderat|profan|toxicity|rekognition|perspective|nsfw|csam|report|block|ban(ned)?' "$BACKEND"
```

Interpretation: if users create content other users can see, E1 applies in full. List every
surface and the mechanism found for each.

## age

```sh
rg -n -i 'DeclaredAgeRange|AgeRangeService|requestAgeRange|ageRange|PermissionKit|SignificantChange' -t ts -t js -t swift -t objc .
rg -n -i 'birth|dateOfBirth|\bdob\b|age.?gate|under.?13|under.?16|minor' -t ts -t js .
```

## health

```sh
rg -n 'healthkit|HealthKit|AppleHealth|queryQuantitySamples|saveQuantitySample|saveWorkout|requestAuthorization|HKQuantityTypeIdentifier|isHealthDataAvailable' -t ts -t js .
rg -n 'CloudKit|NSUbiquitous|iCloud' -t ts -t js .
```

Interpretation: list every type read and written, then trace each read to its destinations
(G1, G3). HealthKit entitlements come from "native-config" (G4).

## push

```sh
rg -n 'getExpoPushTokenAsync|getDevicePushTokenAsync|registerForPushNotifications|requestPermission|OneSignal|notifee' -t ts -t js .
rg -n -i 'marketing|promo|campaign|newsletter|win.?back|re.?engag|upsell' -t ts -t js .
```
[backend]
```sh
rg -l -i 'apns|fcm|expo-server-sdk|exp\.host/--/api/v2/push|sendPush|pushNotification' "$BACKEND"
rg -n -i 'marketing|promo|campaign|win.?back|re.?engag|upsell|announcement' "$BACKEND"
```

## review-prompts

```sh
rg -n 'requestReview|StoreReview|SKStoreReviewController|RequestReviewAction|InAppReview|react-native-rate|action=write-review|itms-apps://' -t ts -t js .
rg -n -i 'rate (us|the app)|enjoy(ing)? (the|this) app|leave (us )?a review|5 stars|five stars' -t ts -t js .
```

## music

```sh
rg -n -i 'MusicKit|apple.?music|MPMusicPlayer|MPMediaLibrary|ApplicationMusicPlayer|SystemMusicPlayer|NSAppleMusicUsageDescription|music\.apple\.com|api\.music\.apple\.com|previewUrl|previews' -t ts -t js -t swift .
rg -n -i 'autoPlay|shouldPlay|isLooping' -t ts -t js .
```
[backend]
```sh
rg -n -i 'api\.music\.apple\.com|developerToken|MusicKit|\.p8|ES256' "$BACKEND"
```

Interpretation: for every music surface, record whether playback is user-initiated, whether
previews play as background audio, and whether each song reference links to Apple Music
(H3).

## contests

```sh
rg -l -i 'prize|sweepstake|giveaway|raffle|reward|winner|win a|leaderboard|challenge|contest|compete' -t ts -t js .
rg -n -i 'official rules|not (a )?sponsor|Apple is not|no purchase necessary' -t ts -t js .
```

## toolchain

```sh
rg -n '"expo"\s*:|"react-native"\s*:' package.json
python3 -I -c 'import json; d=json.load(open("eas.json")); b=d.get("build",{}); print(json.dumps({k: b.get(k) for k in b}, indent=1))'
rg -n 'enableSceneSupport|deploymentTarget|expo-build-properties' app.json app.config.js app.config.ts 2>/dev/null
rg -n 'xcode-version|xcode_version|xcversion|DEVELOPER_DIR|macos-latest|macos-1[0-9]' .github .circleci bitrise.yml fastlane 2>/dev/null
```

Interpretation: resolve the production profile through any `extends` chain and read its
`ios.image`. Map Expo SDK and image to Xcode with `references/facts.json`
(`eas_ios_images`) and compare with `upload_requirements`, per I1. Bare projects: read the CI Xcode
selection. Binary evidence beats both (see "binary").

## hidden-features

```sh
rg -n -i 'review(er)?.?mode|isReviewer|appleReview|inReview|hideForReview|cupertino|unlock.?code|secret.?menu|easter.?egg|RELEASE_DATE|launchDate' -t ts -t js .
rg -n 'tapCount|tapCounter|onLongPress' -t ts -t js .
rg -n 'remoteConfig|getFeatureFlag|isFeatureEnabled|useFeatureFlag|featureFlags?' -t ts -t js .
```
[backend] `rg -n -i 'reviewer|app.?review|cupertino|17\.0\.0\.0/8' "$BACKEND"`

Interpretation: list every flag-gated feature, its default, and whether it is reachable and
described for review (I3).

## ota

```sh
rg -n 'expo-updates|code-push|codePush|hot-updater|revopush' package.json
rg -n 'updates|runtimeVersion|channel' app.json app.config.js app.config.ts eas.json 2>/dev/null
rg -n -i 'eas update|code-push release|codepush' .github scripts package.json 2>/dev/null
ls CHANGELOG* NEXT.md RELEASE* 2>/dev/null
```

## secrets

```sh
rg -n 'sk_live_|sk_test_|rk_live_|-----BEGIN (EC |RSA )?PRIVATE KEY-----|"private_key"\s*:|Bearer [A-Za-z0-9._-]{20,}' -g '!*.lock' .
rg -n '(api[_-]?key|apiKey|secret|token|password)\s*[:=]\s*["\x27][A-Za-z0-9+/_-]{20,}' -t ts -t js -t json .
rg -n 'EXPO_PUBLIC_[A-Z0-9_]*(SECRET|PRIVATE|TOKEN|KEY|PASSWORD)' -t ts -t js -t json .
rg -n 'EXPO_PUBLIC_' --no-ignore --hidden -g '.env*' -g 'eas.json' -g 'app.config.*' -g '!**/node_modules/**' .
rg --files --no-ignore -g '*.p8' -g '*.pem' -g '*service-account*.json' -g '!**/node_modules/**' .
rg -n 'AsyncStorage\.setItem\(.{0,40}(token|jwt|session|password)' -i -t ts -t js .
```

Interpretation: every `EXPO_PUBLIC_*` value is inlined into the shipped JS, so a secret there
is shipped. Publishable keys are not findings (Guards 2). Check whether `.p8` or `.pem` files
are tracked (`git ls-files`) or only local.

## webview-bridges

```sh
rg -n '<WebView' -t ts -t js -l .
rg -n 'onMessage|injectedJavaScript|injectJavaScript|postMessage|originWhitelist|javaScriptCanOpenWindowsAutomatically' -t ts -t js .
```

Interpretation: a WebView that loads third-party interactive content and forwards its
messages to native modules is a J4 (4.7.2) lead.

## native-swift

For native Xcode projects, replace `-t ts -t js` with `-t swift -t objc -t objcpp` in the
recipes above, and use these equivalents:

| Checks | Swift / Objective-C patterns |
|---|---|
| A1-A4 | `Product.products(for:`, `.purchase(`, `Transaction.currentEntitlements`, `AppStore.sync`, `SKPaymentQueue`, `restoreCompletedTransactions`, `isEligibleForIntroOffer` |
| A8 | `AppStore.showManageSubscriptions`, `showManageSubscriptions` |
| B4 | `requestWhenInUseAuthorization`, `requestAlwaysAuthorization`, `AVCaptureDevice.requestAccess`, `PHPhotoLibrary.requestAuthorization`, `CNContactStore().requestAccess` |
| B5 | `PHPickerViewController` and `PhotosPicker` (minimal), `PHPhotoLibrary.requestAuthorization(for: .readWrite)` (full access) |
| C1, C2 | `ATTrackingManager.requestTrackingAuthorization`, `ASIdentifierManager` |
| D1-D5 | `ASAuthorizationAppleIDProvider`, `credentialRevokedNotification`, `getCredentialState`, `GIDSignIn`, `LoginManager` |
| F4, F5 | `import DeclaredAgeRange`, `AgeRangeService`, `import PermissionKit` |
| G1-G4 | `HKHealthStore`, `requestAuthorization(toShare:read:)`, `isHealthDataAvailable()`, `HKObserverQuery`, `enableBackgroundDelivery` |
| H1 | `registerForRemoteNotifications`, `UNUserNotificationCenter`, `requestAuthorization(options:)` |
| H2 | `SKStoreReviewController.requestReview`, `@Environment(\.requestReview)`, `AppStore.requestReview` |
| H3 | `import MusicKit`, `MusicAuthorization.request`, `ApplicationMusicPlayer`, `SystemMusicPlayer` |
| I5 | `performSelector`, `NSClassFromString`, `dlopen`, `dlsym` |
| I6 | `UIWebView` |
| J1, J4 | `WKWebView`, `WKScriptMessageHandler`, `addScriptMessageHandler`, `evaluateJavaScript` |

Dependencies come from `Podfile.lock` and `Package.resolved` instead of package.json.
Extensions (widgets, App Clips, notification service extensions) have their own Info.plist,
entitlements, and privacy manifest; audit each target, and remember that extensions may not
show ads (2.5.16, 2.5.18).
