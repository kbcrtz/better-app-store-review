# Guideline checks

Baseline: the Apple App Review Guidelines date in `facts.json` (`baseline`), read in full,
plus the Apple policy pages and announcements listed in `apple-changes.md`. Dates and tool
mappings that change often live in `facts.json`; checks reference them by key. Guideline numbers below are the current ones; do not cite a number that
is not in the numbering table at the end of this file without re-reading Apple's page.

Each domain section is owned by one auditor. Every auditor also reads "False-positive
guards" before reporting. Recipes referenced as "D:<section>" live in `detection.md`.

## Severity and category

Severity:
- **BLOCKER**: App Review will reject (deterministic or near certain), App Store Connect will
  refuse the upload, or a security emergency.
- **HIGH**: likely rejection depending on what the reviewer exercises, or a violation Apple
  enforces after approval (removal, account termination).
- **MEDIUM**: judgment-heavy, quality, or submission friction; low rejection likelihood.

Category (the `category` field in findings):
- `review`: App Review rejection risk.
- `upload`: App Store Connect refuses the build or blocks submission.
- `removal`: post-approval enforcement (removal, Developer Program termination).
- `security`: data-security emergency; ships nothing until fixed.
- `legal`: obligation outside App Review (state, national, or regional law). Reported
  separately; never counts toward the verdict.
- `hygiene`: quality issue with no direct guideline hook.

---

## A. payments (3.1.x, 3.2.x, 2.1(b), 4.9, 4.10)

### A1. Digital goods use IAP; purchase link-outs are storefront-gated

- **Guidelines:** 3.1.1, 3.1.1(a), 3.1.3 (and 3.1.3(a)-(g) exemptions).
- **Severity / category:** BLOCKER / review (see the scoped cases below).
- **Applies when:** the app unlocks features, content, subscriptions, currencies, boosts, or
  any digital good, or an external payment SDK or checkout link exists.
- **Detect:** D:external-payment and D:storefront. Read every purchase surface. Also look for
  self-built unlock mechanisms: license keys, promo or unlock codes, QR codes, AR markers,
  crypto wallets that unlock features (3.1.1 forbids all of these).
- **Violation:**
  - A digital purchase completed inside the app by Stripe, PayPal, Braintree, or any non-IAP
    processor (payment sheet, card form, web checkout in a WebView).
  - A button, link, or call to action toward a non-IAP purchase that is shown on every
    storefront, or gated by device locale, region setting, timezone, or IP address instead
    of the App Store storefront.
  - Selling post "boosts" or ads displayed in the same app outside IAP (3.1.3(g)).
  - Unlocking features with a code or key not sold through IAP.
- **Scoped cases:**
  - United States storefront: since May 1, 2025, apps on the US storefront may include
    buttons, external links, and other calls to action to non-IAP purchase methods without
    an entitlement. The gate must use the StoreKit storefront (country code of the App Store
    account), not the device locale. Report a correctly gated US-only link as compliant.
  - Web-only digital purchasing with no IAP on the US storefront (outside reader apps): HIGH,
    not BLOCKER. 3.1.1 still says features must be unlocked with IAP; the US change covers
    calls to action. Recommend keeping IAP for the same items.
  - Other regions: the StoreKit External Purchase Link Entitlement (link to a permitted
    destination) and regional alternative-payment terms (EU single business terms effective
    October 1, 2026 allow alternative payment options alongside IAP; Japan from iOS 26.2;
    Brazil from iOS 26.5; Republic of Korea) are lawful only with the entitlement or signed
    terms and only on those storefronts. Code can show the gate; the entitlement is
    needs-user.
- **Not a violation:** physical goods or real-world services consumed outside the app
  (3.1.3(e) requires a non-IAP method, so IAP for these is itself wrong); real-time
  one-to-one person-to-person services such as a live personal trainer session (3.1.3(d));
  one-to-few or one-to-many live classes are NOT exempt and need IAP. Reader apps accessing
  previously purchased content (3.1.3(a)); enterprise sales (3.1.3(c)); multiplatform access
  to items also sold via IAP (3.1.3(b)); optional person-to-person monetary gifts where 100%
  reaches the recipient and no digital content is tied to it (3.2.1(vii)).
- **Fix:** route digital purchases through StoreKit (react-native-purchases, react-native-iap,
  expo-iap). Gate any link-out on the StoreKit storefront country code and document the
  storefront restriction in App Review notes.

### A2. Paywall and subscription disclosures

- **Guidelines:** 3.1.2(c), Schedule 2 of the Apple Developer Program License Agreement,
  Apple's subscription sign-up requirements (developer.apple.com/app-store/subscriptions).
- **Severity / category:** BLOCKER / review.
- **Applies when:** any auto-renewable subscription or paid unlock is offered.
- **Detect:** D:paywall. Read every purchase screen, including onboarding paywalls, upsell
  sheets, and remote paywalls (RevenueCat Paywalls, Superwall, Adapty: their layout lives in
  a dashboard, so mark layout items needs-user and check only what code controls).
- **Each purchase screen must show:**
  1. Subscription name, duration, and what the user gets during the period.
  2. Full renewal price, clear, prominent, and localized: rendered from the StoreKit product
     (`priceString`, `localizedPriceString`, `displayPrice`), never a hardcoded "$4.99".
  3. The amount that will be billed as the most prominent pricing element. Per-week or
     per-month breakdowns of an annual price, and "save 40%" badges, must be smaller and
     subordinate.
  4. For free trials: trial length and the price billed after the trial.
  5. A way to restore purchases or sign in (see A3).
  6. Tappable Terms of Use (EULA) and Privacy Policy links in the app; the same two links must
     also exist in App Store Connect metadata (ASC checklist).
  7. Auto-renewal statement ("renews automatically until canceled") is Schedule 2 practice;
     flag its absence as part of this finding, not alone.
- **Violation:** "Unlock Pro, $1.99/week" in large type with the $103.48/year billed amount in
  footnote text; hardcoded prices; trial copy without the post-trial price.
- **Fix:** build the price block from StoreKit product data, make the billed amount the
  headline price, add the trial terms and both links.

### A3. Restore purchases

- **Guidelines:** 3.1.1 ("restore mechanism for any restorable in-app purchases"); Apple
  subscription sign-up requirements.
- **Severity / category:** BLOCKER / review.
- **Applies when:** non-consumables or subscriptions exist. Consumables alone do not need it.
- **Detect:** `rg -n 'restorePurchases|restoreTransactions|syncPurchases|getAvailablePurchases|restoreCompletedTransactions|AppStore\.sync' -t ts -t js .`.
  Confirm a visible control reaches it (paywall and/or settings), not just a dead function.
- **Fix:** add a Restore Purchases control on the paywall and in settings.

### A4. Trial and offer honesty

- **Guidelines:** 3.1.2(a) free trials, 3.1.1 non-subscription trials, 5.6 ("trick them into
  making unwanted purchases"), 3.1.2(a) bait-and-switch.
- **Severity / category:** HIGH / review.
- **Detect:** trial wording on paywalls (`rg -n 'free trial|try free|days free|trial' -i -t ts -t js .`),
  then check whether the copy is gated on eligibility
  (`checkTrialOrIntroductoryPriceEligibility`, `introductoryPrice`, `isEligibleForIntroOffer`,
  `eligibleIntroOffer`). Non-subscription trials must be a Non-Consumable at price 0 named
  "XX-day Trial" and state duration, what stops working, and downstream charges.
- **Violation:** "Start your free trial" shown to users who already consumed the intro offer
  and will be charged immediately; countdown or scarcity copy that is not true.
- **Fix:** gate trial copy on StoreKit eligibility; fall back to plain pricing.

### A5. Subscription mechanics

- **Guidelines:** 3.1.2(a), 3.1.2(b).
- **Severity / category:** MEDIUM / review.
- **Detect:** product identifiers and entitlement logic.
- **Violation:** subscription period under 7 days; entitlement tied to one device instead of
  the account (subscriptions must work on all of the user's devices where the app exists);
  requiring social posting, contact upload, or invites before delivering what was paid for;
  removing features that existing paid users already bought when moving to subscriptions;
  multiple subscription groups that let a user buy overlapping plans by accident (3.1.2(b)).
- **Fix:** one subscription group with levels; entitlements on the account; honor legacy
  purchases.

### A6. Credits, loot boxes, gifting, gift cards

- **Guidelines:** 3.1.1.
- **Severity / category:** HIGH / review (only when present).
- **Violation:** IAP credits that expire; randomized paid items without odds shown before
  purchase; digital gift cards sold outside IAP; gifted IAP items refundable to anyone but
  the purchaser.

### A7. Paid features must not depend on permissions or system features

- **Guidelines:** 5.1.1(ii) ("Paid functionality must not be dependent on or require a user
  to grant access to this data"), 5.1.2(i) (no requiring push, location, or tracking to
  access features or to receive compensation), 4.10.
- **Severity / category:** HIGH / review.
- **Detect:** read tier gating and reward logic. Search reward copy:
  `rg -n 'enable (notifications|location|tracking)|turn on (notifications|location)' -i -t ts -t js .`.
- **Violation:** "Enable notifications to get 7 days of Pro free"; paywalled access to a bare
  OS capability (push delivery itself, camera itself, background refresh, Apple Music
  access, iCloud storage, Screen Time APIs) per 4.10.
- **Not a violation:** paywalling your own feature that happens to use the camera (for
  example AI food scanning) is your functionality, not the camera itself.
- **Fix:** gate your features and content, never consent or OS capabilities.

### A8. Subscription management and cancellation paths

- **Guidelines:** 3.1.2, 5.6 (manipulative practices), Apple account-deletion guidance.
- **Severity / category:** MEDIUM / review.
- **Detect:** `rg -n 'showManageSubscriptions|apps\.apple\.com/account/subscriptions|manage.?subscription|cancel.?subscription' -i -t ts -t js .`.
- **Violation:** a "Cancel subscription" button that only flips a server flag while Apple
  keeps billing; retention mazes before reaching the Apple management sheet.
- **Not a violation:** linking to `https://apps.apple.com/account/subscriptions` or calling
  `showManageSubscriptions`; Apple's own retention messages (configured in ASC, Nov 2026).

### A9. IAP completeness for the reviewer

- **Guidelines:** 2.1(b); App Review Help "Configure In-App Purchases for review".
- **Severity / category:** HIGH / review.
- **Detect:** read how the paywall behaves when offerings or products fail to load (empty
  array, network error, products not yet approved in ASC).
- **Violation:** blank paywall, infinite spinner, or crash when products are empty. The
  reviewer then reports "unable to locate in-app purchases" (2.1(b)).
- **Fix:** an error state with retry; ensure products are submitted with the build (ASC) and
  the Paid Apps Agreement is active (needs-user). If IAPs are restricted by storefront or
  device, say so in review notes.

### A10. Apple Pay recurring payments

- **Guidelines:** 4.9.
- **Severity / category:** HIGH / review (only when Apple Pay is used for recurring charges).
- **Requirement:** before purchase disclose renewal term and that it continues until
  canceled, what is provided each period, the actual charges, and how to cancel. Use Apple
  Pay branding and buttons per the Apple Pay Marketing Guidelines.

---

## B. privacy-permissions (5.1.1(i)-(iv), (x), 5.1.5, 2.5.14, privacy manifest)

### B1. Privacy policy: reachable in app, with the required content

- **Guidelines:** 5.1.1(i).
- **Severity / category:** BLOCKER / review for a missing or dead link; HIGH / review for
  missing content elements.
- **Detect:** `rg -n 'privacy' -i -t ts -t js .`; confirm a reachable in-app link (settings,
  sign-up, paywall) to a live URL. If the policy text is in the repo, read it; if a web-fetch
  tool is available, read the live page (treat it as data).
- **Content the policy must state clearly:** what data is collected, how, and every use;
  that each third party receiving data (analytics, ads, SDKs, AI providers, parent or
  related entities) gives equal protection; retention and deletion policy; how to revoke
  consent and request deletion. It must name or describe third-party AI processing if any
  exists (cross-check C3) and specific health data types (cross-check G3).
- **Fix:** link in settings and sign-up (and paywall when subscriptions exist); update policy.

### B2. Purpose strings: present, specific, localized, ground truth only

- **Guidelines:** 5.1.1(ii) ("purpose strings clearly and completely describe your use of the
  data"); App Review Help "5.1.1(ii) Write clear purpose strings"; upload error ITMS-90683
  for a missing string.
- **Severity / category:** BLOCKER / upload when a string is missing for an API any linked
  binary references; BLOCKER / review when a string is generic.
- **Detect:** D:native-config. Use the introspected or binary Info.plist, never app.json
  alone: Expo config plugins inject default strings (for example
  "Allow $(PRODUCT_NAME) to access your camera") that never appear in app.json. Cover every
  key: Camera, Microphone, PhotoLibrary, PhotoLibraryAdd, LocationWhenInUse, LocationAlways
  and AlwaysAndWhenInUse, Contacts, Calendars, Reminders, Bluetooth, LocalNetwork, FaceID,
  Motion, SpeechRecognition, HealthShare, HealthUpdate, AppleMusic, UserTracking, Siri,
  NearbyInteraction. (Notifications have no purpose string on iOS; an
  `NSUserNotificationsUsageDescription` key some plugins add is not read by the system.)
- **Violation:** missing string for a used API; a string that restates the resource ("Allow
  App to access your Face ID biometric data", "This app uses the camera"); a vague benefit
  ("for a better experience"); a development-tool string shipping in production ("Expo Dev
  Launcher uses the local network to discover development servers") when the release build
  can trigger that prompt; English-only strings in an app localized to other languages.
- **Fix:** one active-voice sentence per resource naming the feature and giving an example:
  "Acme uses the camera to scan receipts so you can track expenses." Set it via the plugin's
  option (for example the `faceIDPermission` or `microphonePermission` plugin option), or
  `false` to remove the key when the feature is unused and the plugin supports it. Localize
  with `InfoPlist.strings` (bare) or `locales` in app config (Expo).

### B3. Privacy manifest and required-reason APIs

- **Guidelines:** not an App Review guideline: an App Store Connect upload requirement since
  May 1, 2024 (ITMS-91053 missing API declaration) plus Apple's third-party SDK list that
  must ship privacy manifests and signatures (ITMS-91061). 5.1.1 for accuracy of labels.
- **Severity / category:** BLOCKER / upload.
- **Detect:** D:privacy-manifest. Build the union of `NSPrivacyAccessedAPIType` and reasons
  from every `PrivacyInfo.xcprivacy` under installed native packages, then compare it with
  the app-level manifest (bare: `ios/<App>/PrivacyInfo.xcprivacy` in the app target; Expo:
  `expo.ios.privacyManifests` plus the template defaults visible in a built IPA). Expo
  documents that Apple does not correctly parse manifests of static CocoaPods
  dependencies, so library reasons may need copying into the app-level manifest.
- **Violation:** a required-reason API category (UserDefaults, FileTimestamp,
  SystemBootTime, DiskSpace, ActiveKeyboards) used by app or library code with no declared
  reason at app level; a listed SDK (Firebase*, GoogleSignIn, OneSignal, Lottie, hermes,
  SDWebImage, and others on Apple's list) at a version without its manifest;
  `NSPrivacyTracking` false while tracking SDKs run (cross-check C1).
- **Fix:** declare the union in `expo.ios.privacyManifests` or the bare manifest; upgrade
  listed SDKs. Confirm by uploading to TestFlight: Apple emails missing reasons within
  minutes.

### B4. Permission requests: timing, pre-prompts, denial handling

- **Guidelines:** 5.1.1(iv) (no manipulating, tricking, or forcing consent; offer
  alternatives when declined); HIG Privacy "Pre-alert screens" rules.
- **Severity / category:** HIGH / review.
- **Detect:** D:permission-flows. For each `request*Permission*` call, read the screen that
  precedes it and the code path after denial.
- **Violation:**
  - A custom pre-permission screen with more than one button, with a close, skip, "Not now",
    or "Maybe later" path that avoids the system alert, or with a button titled "Allow" or
    similar (HIG: one button, titled "Continue" or "Next").
  - Incentives for granting a permission, imitation alert UI, or arrows pointing at the
    system Allow button.
  - Requesting at launch a permission the core experience does not need.
  - After denial, the whole app or an unrelated feature is blocked, or the app loops the
    request; no manual alternative where one is possible (manual address instead of
    location, manual entry instead of HealthKit import).
- **Not a violation:** explanatory copy in context; a Settings deep link after denial;
  legally required consent screens.
- **Fix:** request in context at first use; single "Continue" pre-alert at most; degrade
  gracefully on denial.

### B5. Data minimization and out-of-process pickers

- **Guidelines:** 5.1.1(iii).
- **Severity / category:** MEDIUM / review.
- **Detect:** `rg -n 'requestMediaLibraryPermissionsAsync|MediaLibrary\.requestPermissionsAsync|requestPermissionsAsync\(\)|Contacts\.requestPermissionsAsync|requestBackgroundPermissionsAsync|Always' -t ts -t js .`.
- **Violation:** requesting full Photos access only to pick an image (expo-image-picker's
  `launchImageLibraryAsync` uses the system picker and needs no library permission on
  current iOS); full Contacts access to pick one contact; Always location where When In Use
  suffices; requesting HealthKit types the app never reads.
- **Not a violation:** write-only photo access to save images (`NSPhotoLibraryAddUsageDescription`,
  `requestPermissionsAsync(true)` write-only); full library access for a real gallery feature.
- **Fix:** use pickers and share sheets; request the narrowest scope.

### B6. Login, personal data, and consent requirements

- **Guidelines:** 5.1.1(ii) (consent even for "anonymous" data; easy way to withdraw),
  5.1.1(x) (basic contact info must be optional unless core), 5.1.1(v) (no requiring
  personal information unless relevant to core functionality or required by law).
- **Severity / category:** HIGH / review (judgment).
- **Detect:** read sign-up and onboarding field validation (which fields are required).
- **Violation:** mandatory phone number, birthday, or gender in an app whose core features
  do not need them; analytics with no consent path or withdrawal control where the app
  claims consent-based processing.
- **Not a violation:** fitness metrics (height, weight, age) required for core calculations
  the app explains.

### B7. Recording consent and indicators (including session replay)

- **Guidelines:** 2.5.14 (explicit consent plus clear visual or audible indication when
  recording, logging, or otherwise recording user activity, including screen recordings and
  other user inputs); 5.1.2(i) disclosure.
- **Severity / category:** HIGH / review.
- **Detect:** D:recording. Session replay or heatmap SDKs (PostHog session replay,
  FullStory, Smartlook, UXCam, LogRocket, Microsoft Clarity, Instabug repro) and their
  enablement flags; camera or microphone recording code.
- **Violation:** session replay enabled for all users with no consent and no disclosure;
  audio recording without an on-screen recording indicator.
- **Fix:** disable replay, or gate it on explicit opt-in with masking of inputs, and disclose
  it in the privacy policy and App Privacy labels.

### B8. Location services

- **Guidelines:** 5.1.5.
- **Severity / category:** MEDIUM / review.
- **Violation:** location used where not directly relevant; background location without a
  visible user benefit; location for emergency services or vehicle control.

### B9. SafariViewController must be visible

- **Guidelines:** 5.1.1(vii).
- **Severity / category:** MEDIUM / review.
- **Violation:** an in-app browser or SFSafariViewController hidden, zero-sized, or
  obscured, especially to set cookies or track.

---

## C. data-sharing-tracking (5.1.2, ATT, 2.5.18, 5.1.1(viii))

### C1. App Tracking Transparency when tracking occurs

- **Guidelines:** 5.1.2(i); Apple "User privacy and data use" (definition of tracking).
- **Severity / category:** BLOCKER / review.
- **Applies when:** any ad network, attribution, or deferred-deep-linking SDK, IDFA access,
  or data sharing with data brokers.
- **Tracking includes:** linking app data with other companies' data for targeted ads or ad
  measurement; sharing with data brokers; including an SDK that combines your data with
  other apps' data for ads even if you do not use that feature; third-party deep-linking or
  deferred deep-linking that creates a shared identity across companies; tracking inside a
  WebView that is part of app functionality; using hashed email or phone as a substitute
  identifier.
- **Not tracking:** first-party analytics not shared for advertising; IDFV used across the
  same developer's apps; on-device-only linking; fraud prevention or security use.
- **Detect:** D:signal-deps tracking group; `rg -n 'requestTrackingPermissionsAsync|requestTrackingAuthorization|AppTrackingTransparency|advertisingIdentifier|getAdvertisingId|IDFA' -t ts -t js .`;
  NSUserTrackingUsageDescription in D:native-config.
- **Violation:** a tracking SDK initialized with no ATT request; ATT absent while App Privacy
  answers say "tracking".
- **Fix:** expo-tracking-transparency (or native ATT), request before the SDK collects;
  configure SDKs to wait for authorization.

### C2. ATT behavior: timing, no gating, no incentives, reachable for review

- **Guidelines:** 5.1.2(i), 5.1.1(iv), HIG "Tracking requests".
- **Severity / category:** HIGH / review.
- **Violation:** SDK collecting before the ATT promise resolves; features gated on allowing
  tracking; rewards for allowing; a pre-prompt imitating the alert or annotating the screen;
  a vague NSUserTrackingUsageDescription; an ATT prompt the reviewer cannot reach (shown
  only deep in a flow), which produces a 2.1 "information needed" rejection.
- **Also flag (MEDIUM):** an ATT prompt with no tracking behind it; remove it or justify it.
- **Note:** iOS 27.2 adds an optional alternative ATT prompt in the EU (mandatory in
  Germany, France, Italy, Poland, Romania); when-to-ask rules are unchanged.

### C3. Personal data sent to third-party AI (new rule, November 13, 2025)

- **Guidelines:** 5.1.2(i) ("You must clearly disclose where personal data will be shared
  with third parties, including with third-party AI, and obtain explicit permission before
  doing so"); 5.1.1(i) policy content; App Review Help asks for AI services in review notes.
- **Severity / category:** BLOCKER / review when personal data (photos, voice, messages,
  journal or note text, health or fitness logs, location, identity) reaches a third-party AI
  with no explicit permission UI; HIGH when a permission exists but does not name the data
  or the third party.
- **Applies when:** D:third-party-ai finds an AI SDK or endpoint in the app or the backend.
- **Detect:** trace each call site from the user action to the provider: client-direct calls
  and backend proxies both count (a backend relaying a user's photo to an AI API is still
  sharing it). Then find the consent surface shown before the first send and how the choice
  is stored and honored.
- **Violation:** "Scan food photo" uploads the image to a server that forwards it to an AI
  provider, with no prior disclosure and opt-in; consent only buried in Terms.
- **Not a violation:** on-device models (Apple Foundation Models framework, Core ML, Vision);
  sending only non-personal data (public exercise names, app-authored prompts).
- **Fix:** before first use, a clear sheet stating what is sent, to which provider (or "a
  third-party AI service"), and why, with an explicit opt-in; store the choice; a settings
  toggle to withdraw; policy and App Privacy labels updated; review notes list the provider.

### C4. Sensitive data in SDK and analytics flows

- **Guidelines:** 5.1.2(ii) (no repurposing), (iii) (no covert profiles), (iv) (no contact
  databases; no installed-apps collection for analytics or ads), (vi) (HealthKit, ClassKit,
  HomeKit, depth or face data, Camera and Photo APIs data not for marketing, advertising, or
  use-based data mining), 5.1.3(i).
- **Severity / category:** HIGH / review.
- **Detect:** D:analytics-payloads; `rg -n 'LSApplicationQueriesSchemes' -A 30 .` in native
  config (a long scheme list used to probe installed apps).
- **Violation:** HealthKit values, photos, precise location, contacts, or message content in
  third-party analytics events or identify() traits; canOpenURL probing of many apps for
  analytics.
- **Fix:** strip sensitive fields from events; aggregate on your own server.

### C5. Contacts-based invites and messaging

- **Guidelines:** 5.1.2(v).
- **Severity / category:** HIGH / review (when present).
- **Violation:** "Select all" or default-all contact selection; sending without showing the
  message text and sender; contacting people from Contacts or Photos without an explicit,
  individual user action.

### C6. Advertising rules

- **Guidelines:** 2.5.18, 5.1.2(vi).
- **Severity / category:** HIGH / review (when an ad SDK is present).
- **Violation:** ads in extensions, widgets, notifications, keyboards, App Clips, or watchOS
  apps; ads inappropriate for the age rating; no in-app way to see why an ad was targeted;
  targeting from health, kids, or school data; interstitials without a clear ad label or an
  easily visible close or skip button; no way to report inappropriate ads.

### C7. Compiling personal data from other sources

- **Guidelines:** 5.1.1(viii).
- **Severity / category:** HIGH / review.
- **Violation:** building profiles of people from public databases, scraping, or any source
  other than the user, without explicit consent.

---

## D. accounts-login (5.1.1(v), 4.8, 2.5.13, Guideline 4)

### D1. In-app account deletion

- **Guidelines:** 5.1.1(v); App Review Help "5.1.1(v) Offering account deletion in your app".
- **Severity / category:** BLOCKER / review.
- **Applies when:** the app creates accounts, including automatically created guest accounts.
- **Detect:** D:accounts. Read the UI flow and the backend handler it calls (when the
  backend is in the repo).
- **Requirements:**
  - Easy to find (typically account settings) and initiated inside the app.
  - Deletes the account record and associated personal data, including user-generated
    content shared with others (posts, photos, comments, reviews), except data the
    developer is legally required to keep (and the user is told what is kept).
  - Deactivate-only is insufficient (it may be offered in addition).
  - Outside regulated industries (5.1.1(ix)), no phone call, email, support chat, or other
    support flow required.
  - Re-authentication or a confirmation code is allowed; making it unnecessarily hard is not.
  - If a website step is needed, the in-app button deep-links directly to the page where
    deletion is completed. A link to a homepage or help center is a violation.
  - Manual or delayed deletion is allowed if the user is told how long it takes and gets a
    confirmation when done.
  - Available to everyone, not only users in GDPR or CCPA regions.
  - With an active auto-renewable subscription: tell the user billing continues through
    Apple and offer `showManageSubscriptions` or
    `https://apps.apple.com/account/subscriptions`. Scheduling deletion at expiry is
    allowed only alongside an immediate-delete option.
- **Violation:** "Delete account" opens `mailto:support@...`; only "Deactivate"; backend sets
  `deleted = true` and keeps posts and photos visible or stored with no stated legal reason.
- **Not a violation:** `Linking.openURL('https://example.com/account/delete')` that lands
  directly on the deletion page.
- **Fix:** in-app flow with confirmation that calls a hard-delete (or scheduled hard-delete)
  endpoint covering UGC and media storage.

### D2. Sign in with Apple: token revocation and account-change notifications

- **Guidelines:** 5.1.1(v) FAQ; TN3194 "Handling account deletions and revoking tokens for
  Sign in with Apple".
- **Severity / category:** HIGH / review.
- **Applies when:** Sign in with Apple is offered.
- **Detect:** backend: `rg -n 'appleid\.apple\.com/auth/(revoke|token)|authorizationCode|refresh_token' "$BACKEND"`;
  client: whether the authorization code is sent to the server.
- **Violation:** account deletion that never calls `https://appleid.apple.com/auth/revoke`;
  no stored refresh token (authorization code never exchanged), making revocation
  impossible; no handling of credential-revoked or `consent-revoked` events.
- **Note (legal for Korea-based developers):** since January 1, 2026, developers based in
  the Republic of Korea must register a server-to-server notification endpoint when creating
  or updating a Services ID.
- **Fix:** exchange the authorization code at sign-in, store the refresh token, revoke on
  deletion, register the notification endpoint.

### D3. Sign in with Apple relay email domain change (2026)

- **Guidelines:** Apple announcement "Update: New domain for Sign in with Apple" (August 24,
  2026); failures surface as 2.1 bugs during review.
- **Severity / category:** HIGH / review.
- **Detect:** `rg -n 'privaterelay\.appleid\.com|private\.icloud\.com|disposable|blocklist|allowlist' -i . "$BACKEND"`
  (app and backend).
- **Violation:** email validation, allowlists, or disposable-email filters that accept only
  `privaterelay.appleid.com`, or block unknown domains, so new Sign in with Apple users on
  `private.icloud.com` cannot register. Reviewers often use Hide My Email.
- **Fix:** accept both relay domains; never block `icloud.com` (Hide My Email stays there).

### D4. Login services equivalence

- **Guidelines:** 4.8 (current text).
- **Severity / category:** BLOCKER / review.
- **Applies when:** a third-party or social login (Google, Facebook, X, LinkedIn, Amazon,
  WeChat, and similar) sets up or authenticates the user's primary account.
- **Requirement:** also offer, as an equivalent option, a login service that limits data
  collection to name and email, lets users keep their email private, and does not collect
  app interactions for advertising without consent. Sign in with Apple satisfies this.
- **Exempt:** only the company's own account system; alternative-marketplace login;
  education, enterprise, or business accounts; government or industry citizen ID;
  a client for a specific third-party service whose content requires that account.
- **Detect:** D:accounts; social login with no Apple or other qualifying option is the
  violation. Read the login and sign-up screens.
- **Fix:** add expo-apple-authentication (or the Invertase module) on the same screens with
  comparable prominence, using Apple's standard button.

### D5. Sign in with Apple experience

- **Guidelines:** 4 (design), 4.8, HIG Sign in with Apple.
- **Severity / category:** HIGH / review.
- **Violation:** asking for name or email again after Sign in with Apple provided them
  (commonly reported as a Guideline 4 design rejection); a custom-drawn Apple button with the wrong logo
  or wording instead of `AppleAuthenticationButton`.
- **Not a violation:** asking for app-specific profile data (username, fitness goals).

### D6. Login walls and social credentials

- **Guidelines:** 5.1.1(v).
- **Severity / category:** HIGH / review (judgment).
- **Violation:** a mandatory account before any use when the app has no significant
  account-based features; requiring a specific social network login when the core is not
  that network; storing social network access or refresh tokens on your servers (tokens may
  only be used from the app while in use); no in-app way to disconnect a linked social
  network.
- **Not a violation:** social, sync, or cloud-backed apps where the account is the product.

### D7. Web-based sign-up or sign-in

- **Guidelines:** 4 (Design), cited in Apple's account-deletion FAQ.
- **Severity / category:** HIGH / review.
- **Detect:** `rg -n '(openURL|openBrowserAsync)\(.{0,80}(signup|sign-up|register|login|signin|sign-in)' -i -t ts -t js .`.
- **Violation:** sending users to the default browser to register or log in.
- **Not a violation:** OAuth through `ASWebAuthenticationSession`
  (expo-auth-session, `WebBrowser.openAuthSessionAsync`).

### D8. Face ID and biometrics

- **Guidelines:** 2.5.13.
- **Severity / category:** MEDIUM / review.
- **Violation:** facial authentication via ARKit or camera instead of LocalAuthentication
  (expo-local-authentication); no alternate method for users under 13; missing or generic
  NSFaceIDUsageDescription (cross-check B2).

### D9. Reviewer access

- **Guidelines:** 2.1(a); App Review Help "Provide information for a complete review".
- **Severity / category:** HIGH / review (needs-user for credentials).
- **Detect:** login methods requiring codes (SMS OTP, email magic link, 2FA).
- **Requirement:** a demo account that works through review, an authentication code given
  in review notes in advance, or an Apple-approved demo mode. For subscriptions, a demo
  account with an expired subscription so the full purchase flow is reviewable.
- **Violation (code):** SMS-only login with no way to provide a reviewer a working code;
  demo bypass logic that is undocumented (that is a 2.5.19 hidden feature; document it).

---

## E. ugc-safety (1.1, 1.2, 1.2.1, 1.5)

### E1. The four required UGC mechanisms

- **Guidelines:** 1.2. The current text names social media, user-generated content
  platforms, and AI content creation apps as in scope; random or anonymous chat was
  clarified as in scope on February 6, 2026; nonconsensual intimate imagery, including
  AI-generated imagery, was added on October 16, 2026.
- **Severity / category:** BLOCKER / review.
- **Applies when:** users create, generate, upload, share, or send content other users can
  see: posts, comments, replies, photos, profiles, bios, usernames, direct messages, group
  chats, reviews, shared workouts or routines, AI-generated images or text shown to others.
- **Detect:** D:ugc. Enumerate every surface where one user sees another user's content and
  verify each mechanism on each surface, in the UI and in the backend:
  1. Filtering before content is posted: server-side text moderation, image moderation for
     uploaded images, or a review queue. Client-only filtering is weak evidence.
  2. Reporting from each content type and from profiles, persisted server-side, with a path
     for timely action.
  3. Blocking abusive users: hides their content from the blocker and prevents contact,
     enforced server-side.
  4. Published contact information reachable in the app.
- **Reviewer practice (from App Review's standard 1.2 rejection message, not guideline
  text):** reviewers also ask for Terms (EULA) acceptance that states zero tolerance for
  objectionable content and abusive users, action on reports within 24 hours (remove content,
  eject the user), and blocks that remove content from the blocker's feed instantly and
  notify the developer. Check for these and report gaps as part of this finding.
- **Violation:** comments with no report action; DMs with no block; image uploads with no
  moderation.
- **Not a violation:** content visible only to its author.
- **Fix:** add the missing mechanism per surface, server-enforced.

### E2. Remediation capability

- **Guidelines:** 1.2 (developer responsibility to remove violating content; failure to
  implement safeguards or remediate after notice can be a Developer Code of Conduct
  violation).
- **Severity / category:** HIGH / removal.
- **Detect:** backend admin or moderator capabilities: delete content, ban or suspend users,
  review reports, takedown of NCII.
- **Violation:** reports stored but nothing can act on them; no way to remove a user's
  content without database access.

### E3. Prohibited UGC patterns and NSFW

- **Guidelines:** 1.2, 1.1.4.
- **Severity / category:** BLOCKER / review when core to the app.
- **Violation:** primarily pornographic UGC, Chatroulette-style or random anonymous chat
  without 1.2 safeguards, "hot or not" rating of real people, threat or bullying platforms,
  apps that generate nudity or sexual imagery of real people ("nudification").
  NSFW from a web-based service must be hidden by default and enabled only on the website.

### E4. Creator content age controls

- **Guidelines:** 1.2.1, 1.2.1(a) (November 13, 2025).
- **Severity / category:** HIGH / review.
- **Applies when:** the app hosts creator experiences (creators author, share, and monetize
  content inside the app).
- **Requirement:** users can identify content that exceeds the app's age rating; an age
  restriction mechanism based on verified or declared age (for example the Declared Age
  Range API) limits underage access; users are told which content costs extra; digital
  sales use IAP.

### E5. Objectionable app-provided content

- **Guidelines:** 1.1.1-1.1.7.
- **Severity / category:** MEDIUM / review (judgment).
- **Violation:** seeded or AI-generated default content that is defamatory, realistically
  violent, sexual, or exploits current tragedies; fake functionality labeled "for
  entertainment" (1.1.6).

---

## F. age-kids (2.3.6, 2.3.8, 1.3, 5.1.4, age assurance)

### F1. Age rating answers implied by code

- **Guidelines:** 2.3.6 (answer honestly); age rating system of July 24, 2025 (4+, 9+, 13+,
  16+, 18+; new questions on in-app controls, capabilities, medical or wellness, violence);
  social media capability question required since September 2026; new descriptors
  "Shared Location" and "Dating and Relationships" (announced November 2, 2026; their
  submission deadlines are in `facts.json` `deadlines`).
- **Output:** not findings. Produce the "Age rating answers implied by code" table in the
  report (see report.md) from code evidence for each capability: User-Generated Content,
  Social Media (redistribute, amplify, or interact with UGC via a feed or similar discovery:
  likes, comments, shares; forces a 13+ minimum unless disabled for under-13 users with at
  least the Declared Age Range API), Messaging and Chat, Advertising, Unrestricted Web
  Access, Parental Controls, Age Assurance, Contests (including sport or fitness contests),
  Loot Boxes, Gambling, Health or Wellness Topics (calorie tracking, dieting advice, exercise
  recommendations), Medical or Treatment Information, Shared Location, Dating and
  Relationships (18+), AI chat or generation (affects content frequency answers).
- **Finding only when code contradicts a claim the app makes,** for example in-app copy or
  config stating social features are disabled for under-13 users with no age check in code
  (HIGH / review, 2.3.6).

### F2. Kids Category

- **Guidelines:** 1.3, 5.1.4.
- **Severity / category:** HIGH / review.
- **Applies when:** the app targets or is listed for children.
- **Violation:** third-party analytics or advertising (narrow exceptions only); personal or
  device information sent to third parties; links out, purchases, or distractions not behind
  a parental gate; missing privacy policy. Once in Kids, an app must keep meeting these
  rules even if the category is later deselected.

### F3. Child-directed wording outside the Kids Category

- **Guidelines:** 2.3.8, 5.1.4.
- **Severity / category:** MEDIUM / review.
- **Violation:** "for kids" or "for children" in the app name, subtitle, icon, screenshots, or
  description of a non-Kids app, or any wording implying children are the main audience.

### F4. Age signals required by guidelines

- **Guidelines:** 1.2.1(a), 4.7.5, social media under-13 option.
- **Severity / category:** HIGH / review (only when those features exist).
- **Detect:** D:age.
- **Violation:** creator content or mini apps exceeding the age rating with no age gate based
  on verified or declared age.

### F5. Age-assurance laws (legal, outside App Review)

- **Category:** legal. Never counts toward the verdict; list in the legal section.
- **Facts:** Texas SB2420 applies to new Apple Accounts in Texas from June 4, 2026 (the
  injunction was lifted); Utah from May 6, 2026; Louisiana from July 1, 2026. Apple supplies
  the Declared Age Range API (age categories, assurance method, whether parental consent is
  required), the Significant Change API under PermissionKit, a StoreKit age-rating property,
  and an App Store Server Notification for revoked parental consent. Australia requires
  certain social media platforms to prevent under-16 accounts (from December 10, 2025).
  Apple blocks downloads of 18+ apps in Australia, Brazil, and Singapore unless the user is
  confirmed adult; developers may have separate obligations.
- **Report:** which of these APIs the code uses (D:age), whether the app has social features
  that could fall under the Australian law, and "confirm obligations with counsel".

---

## G. health-fitness (5.1.3, 1.4.1, 1.4.5, 2.5.1, 5.1.2(vi), 5.2.5)

### G1. Health data use limits

- **Guidelines:** 5.1.3(i) (no use or disclosure to third parties of data from health,
  fitness, and medical contexts, including HealthKit, Motion and Fitness, MovementDisorder,
  and Clinical Health Records APIs, for advertising, marketing, or other use-based data
  mining, except improving health management or approved research); 5.1.2(vi); Apple
  Developer Program License Agreement: HealthKit and Motion and Fitness data only for
  health, motion, or fitness services.
- **Severity / category:** BLOCKER / review.
- **Detect:** D:health. Trace every HealthKit and motion read to its destinations: state,
  your API, analytics calls, ad SDKs, AI providers, exports.
- **Violation:** heart rate, weight, workouts, or sleep values in ad, attribution, or
  analytics SDK events; health data sent to a third-party AI without the C3 consent;
  health data used for marketing emails or push targeting.
- **Fix:** keep health values inside your own health features; strip them from analytics.

### G2. No false HealthKit writes; no personal health data in iCloud

- **Guidelines:** 5.1.3(ii).
- **Severity / category:** BLOCKER / review.
- **Detect:** every HealthKit write (`save`, `saveQuantitySample`, `saveWorkout`,
  `writeSample`), and iCloud use (`CloudKit`, `NSUbiquitousKeyValueStore`, iCloud document
  containers, `com.apple.developer.icloud-*` entitlements).
- **Violation:** writing values the user did not enter or confirm; test or placeholder
  samples; duplicate samples from retries or offline replays (write paths must be
  idempotent); personal health information stored in iCloud or CloudKit.
- **Fix:** write only user-confirmed values with sample metadata identifiers to de-duplicate;
  keep health data off iCloud.

### G3. Disclose the specific health data collected

- **Guidelines:** 5.1.3(i) ("You must disclose the specific health data that you are
  collecting from the device"), 5.1.1(iii).
- **Severity / category:** HIGH / review.
- **Detect:** list every HealthKit type in read and write requests; compare with the privacy
  policy and in-app explanation, and with what the code actually uses.
- **Violation:** requesting broad type sets the app never reads; policy silent on health
  data.

### G4. HealthKit integration must be real and visible

- **Guidelines:** 2.5.1 (HealthKit for health and fitness purposes, integrating with the
  Health app, and indicated in the app description).
- **Severity / category:** HIGH / review.
- **Detect:** entitlements (`com.apple.developer.healthkit`,
  `com.apple.developer.healthkit.access` such as `health-records`,
  `com.apple.developer.healthkit.background-delivery`) versus code that uses each one.
- **Violation:** HealthKit entitlement with no user-visible Health feature; health-records
  access without a clinical records feature; background delivery entitlement with no
  observer query; HealthKit called without `isHealthDataAvailable` checks (Health exists on
  iPad only from iPadOS 17, so iPad review can crash).
- **Fix:** remove unused entitlements; label the Health integration in UI and ASC description.

### G5. Medical and accuracy claims

- **Guidelines:** 1.4.1 (greater scrutiny; disclose data and methodology behind accuracy
  claims; device-sensor-only blood pressure, glucose, blood oxygen, temperature, or x-ray
  measurement is not permitted; remind users to consult a doctor before medical decisions),
  1.4.2 (drug dosage calculators).
- **Severity / category:** HIGH / review.
- **Detect:** marketing and UI copy: `rg -n 'accurate|clinically|diagnos|treat|cure|blood pressure|glucose|oxygen|medical' -i -t ts -t js .`.
- **Violation:** "accurate calories from a photo" without stating it is an estimate and how
  it is computed; diagnosis or treatment advice with no doctor reminder.
- **Fix:** label estimates as estimates, explain the method, add the consult-a-doctor note
  where advice could drive medical decisions.

### G6. Risky challenges

- **Guidelines:** 1.4.5.
- **Severity / category:** MEDIUM / review (judgment).
- **Violation:** urging activities that risk physical harm (extreme fasting, unsafe max-effort
  challenges tied to rewards, dangerous outdoor stunts).

### G7. Activity rings lookalikes

- **Guidelines:** 5.2.5.
- **Severity / category:** MEDIUM / review.
- **Violation:** visualizing Move, Exercise, or Stand data in rings resembling Apple's
  Activity control.

### G8. Regulated medical device status (App Store Connect)

- **Category:** upload (submission blocker), needs-user.
- **Fact:** since March 26, 2026 apps in the EU/EEA, UK, or US whose primary or secondary
  category is Health and Fitness or Medical, or that declare frequent Medical or Treatment
  Information, must declare regulated medical device status (Yes or No) in ASC. Required for
  new apps since then; existing apps must declare by the date in `facts.json` `deadlines`
  or updates are blocked.
- **Report:** in the ASC checklist whenever this domain applies.

---

## H. apple-services-engagement (4.5.x, 5.2.3, 5.2.5, 5.6.1, 3.2.2(x), 5.3, 2.5.11, 2.5.16)

### H1. Push notifications

- **Guidelines:** 4.5.4 (not required for the app to function; no sensitive personal or
  confidential information; promotions or direct marketing only with explicit opt-in via
  consent language in the app UI plus an in-app opt-out), 4.5.3 (no spam, phishing, or
  unsolicited messages via push or Live Activities), 5.1.2(i).
- **Severity / category:** HIGH / review.
- **Detect:** D:push. Read the client permission flow and, when the backend is in the repo,
  every notification type it sends.
- **Violation:** app unusable if notifications are denied; promotional pushes (sales, offers,
  upsells, feature marketing) with no separate in-app marketing opt-in and opt-out; push
  bodies containing health details, passwords, or private message contents for sensitive
  apps.
- **Not a violation:** transactional and social notifications (a friend liked your post),
  reminders the user configured.

### H2. Ratings and review prompts

- **Guidelines:** 5.6.1 (use the provided API; custom review prompts are disallowed);
  Section 3 introduction (no paid, incentivized, filtered, or fake feedback); 3.2.2(x) (no
  forcing ratings, reviews, or other store actions to access functionality).
- **Severity / category:** HIGH / review.
- **Detect:** D:review-prompts.
- **Violation:** custom star-rating modals that send happy users to the App Store; "Do you
  enjoy the app?" gating where "Yes" leads to the review prompt and "No" leads to private
  feedback (filtered feedback); rewards for ratings; a rating required to unlock content.
- **Not a violation:** `StoreReview.requestReview()` (expo-store-review) or
  `RequestReviewAction`; a persistent "Rate on the App Store" row in settings opening
  `https://apps.apple.com/app/id<ID>?action=write-review`.

### H3. Apple Music and MusicKit

- **Guidelines:** 4.5.2(i)-(iii), 5.2.3, 5.2.5, 4.10.
- **Severity / category:** HIGH / review.
- **Applies when:** MusicKit, Apple Music API, Apple Music previews, or music metadata appear.
- **Detect:** D:music.
- **Violation:**
  - Playback of an Apple Music stream that the user did not initiate (autoplay on view), or
    playback without standard play, pause, and skip controls.
  - Previews used for entertainment value, such as a song playing behind a post, photo
    collage, or workout summary (5.2.5); playing a specific song at a specific moment or
    rendering shareable audio or video needs rights-holder licenses (4.5.2(ii)).
  - Music previews shown without a link to the track in Apple Music (5.2.5).
  - Cover art or metadata used outside music playback or playlists, or in marketing
    (4.5.2(ii)).
  - Paywalling or monetizing access to Apple Music itself, or requiring user info for it
    (4.5.2(i), 4.10).
  - Downloading, uploading, or sharing music files from MusicKit (4.5.2(i), 5.2.3).
  - Apple Music user data (library, playlists, favorites) accessed without a purpose string
    that discloses it, shared with third parties beyond supporting the app, or used to
    identify users or target ads (4.5.2(iii)).
  - The MusicKit developer-token signing key (.p8) or a long-lived token in the client
    bundle (also I10).
- **Fix:** user-initiated playback through MusicKit with standard controls; song references
  rendered as links to Apple Music per the Apple Music Identity Guidelines; tokens minted
  server-side.

### H4. Contests, sweepstakes, prizes, betting

- **Guidelines:** 5.3.1 (sponsored by the developer), 5.3.2 (official rules in the app and a
  clear statement that Apple is not a sponsor or involved), 5.3.3 (no IAP credit for
  real-money gaming), 5.3.4 (real-money gaming licensed, geo-restricted, free app), 1.4.5.
- **Severity / category:** HIGH / review.
- **Applies when:** challenges, competitions, leaderboards, giveaways, or raffles offer
  prizes or rewards with real-world value.
- **Detect:** D:contests.
- **Violation:** a prize challenge with no in-app official rules or no "Apple is not a
  sponsor" statement; third-party-sponsored sweepstakes.
- **Not a violation:** leaderboards or badges with no prizes (these still drive the
  Contests age-rating answer, F1).

### H5. Game Center, emoji, Apple marks, Apple products

- **Guidelines:** 4.5.3, 4.5.5, 4.5.6, 5.2.4, 5.2.5.
- **Severity / category:** MEDIUM / review.
- **Violation:** displaying or exploiting Game Center Player IDs; Apple emoji embedded as
  image assets in the binary; implying Apple endorsement or showing an Editor's Choice
  badge; UI confusingly similar to an Apple app; Apple Weather data without WeatherKit
  attribution.

### H6. Widgets, extensions, Live Activities, App Clips, Siri

- **Guidelines:** 2.5.16, 2.5.16(a), 4.4, 4.5.3, 2.5.11, 2.5.18.
- **Severity / category:** MEDIUM / review (when present).
- **Violation:** widgets or notifications unrelated to app content; ads or marketing in
  extensions or App Clips; App Clip features missing from the main app; Live Activities used
  for promotions; intents the app cannot fulfill alone, or ads between a Siri request and
  its fulfillment.

### H7. Scraping Apple

- **Guidelines:** 4.5.1.
- **Severity / category:** MEDIUM / review.
- **Violation:** scraping apple.com, App Store, or ASC pages, or building rankings from them.

---

## I. completeness-software (2.1, 2.3 code-visible, 2.4, 2.5, 1.5, 1.6, toolchain)

### I1. Build toolchain and SDK minimums

- **Guidelines:** App Store Connect upload requirements (minimum Xcode and iOS SDK, minimum
  deployment target) and 2.5.1 (run on the currently shipping OS). The current and upcoming
  minimums, their dates, and the Expo EAS image to Xcode mapping live in
  `references/facts.json` (`upload_requirements`, `min_deployment_target`,
  `eas_ios_images`). Read them there; do not rely on remembered values.
- **Severity / category:** BLOCKER / upload.
- **Detect:** the scanner's `toolchain` block, then D:toolchain to confirm. Expo: the EAS
  image for the production profile (`ios.image` in eas.json, following `extends`; the default
  `auto` picks the SDK's alias). Map SDK and image to Xcode with `eas_ios_images`. Native:
  the CI Xcode selection. Binary evidence beats both: `DTXcode` and `DTSDKName` in a built
  IPA.
- **Violation (BLOCKER):** the resolved Xcode major is below the minimum whose effective date
  has passed (for example an Expo SDK older than the lowest alias in `eas_ios_images`, or an
  image pinned to an old `*-xcode-NN.*`); a deployment target below `min_deployment_target`.
- **Violation (BLOCKER / review, crash on launch):** an Xcode image at or above
  `scene_lifecycle.required_from_xcode_major` (including `latest`) on an Expo SDK below
  `scene_lifecycle.native_from_sdk` without UIKit scene support. Per Expo, such apps do not
  launch on the new iOS; the `flag_sdk` can enable `scene_lifecycle.flag`, older SDKs must use
  `auto` or their SDK alias.
- **Warning (MEDIUM / upload):** the resolved Xcode is below an upcoming minimum in
  `upload_requirements`; plan the SDK or Xcode upgrade before that date.

### I2. App completeness and reviewer-visible quality

- **Guidelines:** 2.1(a), 2.2.
- **Severity / category:** BLOCKER / review.
- **Detect:** D:environment; placeholders:
  `rg -n 'lorem ipsum|placeholder|coming soon|under construction|test(ing)? only' -i -t ts -t js .`;
  debug or tester UI: `rg -n 'Tester|DevMenu|debug(Screen|Menu|Panel)|__DEV__|isInternal|isStaff|SkipButton' -t ts -t js .`.
- **Violation:** production build resolving to localhost or staging; empty tabs or "coming
  soon" screens; dead links (Terms, Privacy, Support); test, tester-only, or debug controls
  rendered in release builds; beta or demo labels (2.2: betas belong in TestFlight).
- **Not a violation:** controls gated by `__DEV__`, a non-production build profile, or an
  internal-only distribution channel that cannot reach App Store builds.

### I3. Hidden, dormant, or undocumented features; bait-and-switch

- **Guidelines:** 2.5.19 (new October 16, 2026; formerly in 2.3.1), 2.3.1(a) (new features
  described specifically in review notes).
- **Severity / category:** BLOCKER / removal.
- **Detect:** D:hidden-features. Review detection, date or remote switches that reveal
  features after approval, secret gestures or tap sequences, unlock codes, obfuscated code
  paths, region checks targeting Cupertino or reviewer accounts.
- **Violation:** `if (remoteConfig.reviewMode) hideTab()`; a remote flag that turns on a
  feature absent from the reviewed experience; behavior that differs for reviewers.
- **Not a violation:** remote flags used as kill switches, or staged rollout of features that
  were present, reachable, and described when reviewed; a documented demo account.
- **Fix:** remove review-conditional logic; describe every flag-gated feature in review notes
  and keep it reachable during review.

### I4. Over-the-air updates

- **Guidelines:** 2.5.2, 2.5.19, Apple Developer Program License Agreement 3.3.1 (interpreted
  code may be downloaded only if it does not change the app's primary purpose by adding
  features inconsistent with its intended and advertised purpose, does not bypass OS
  security, and does not create a storefront for other apps).
- **Severity / category:** HIGH / removal (process risk; code cannot prove intent).
- **Detect:** D:ota. Channels, runtime version policy, publish scripts and CI jobs, and any
  release notes or changelogs in the repo describing features shipped OTA.
- **Violation:** evidence that new features (not fixes) ship via OTA without a reviewed
  binary.
- **Fix:** ship features in reviewed binaries; use OTA for fixes and content.

### I5. Private APIs, downloaded executable code

- **Guidelines:** 2.5.1, 2.5.2.
- **Severity / category:** BLOCKER / review.
- **Detect:** native code you own (bare: `ios`; CNG: local `modules` and `targets` only):
  `rg -n 'performSelector|NSClassFromString|dlopen|dlsym|_private' ios modules targets --glob '!**/Pods/**' 2>/dev/null`;
  JS: `rg -n 'new Function\(|eval\(' -t ts -t js .` and trace whether fetched strings execute.
- **Violation:** private selectors, loading native code at runtime, executing downloaded
  scripts beyond the 3.3.1 interpreted-code limits.

### I6. UIWebView and deprecated technology

- **Guidelines:** 2.5.1; upload error ITMS-90809.
- **Severity / category:** BLOCKER / upload.
- **Detect:** `rg -l 'UIWebView' --no-ignore -g '*.{m,mm,h,swift}' node_modules ios 2>/dev/null` (exclude
  comments by reading hits), or `rg -a -l UIWebView "$APPDIR"` on an unzipped IPA.

### I7. Background modes justified

- **Guidelines:** 2.5.4.
- **Severity / category:** HIGH / review.
- **Detect:** D:native-config for `UIBackgroundModes` (introspected or binary, since plugins
  add modes: expo-audio or expo-av background playback adds `audio`, expo-location
  background adds `location`, expo-notifications can add `remote-notification`,
  background task libraries add `fetch` or `processing`). For each mode, find the code that
  needs it.
- **Violation:** `audio` with no background playback; `location` with no background
  location feature; `voip` without CallKit.
- **Fix:** remove unused modes via the plugin option or infoPlist.

### I8. IPv6

- **Guidelines:** 2.5.5.
- **Severity / category:** MEDIUM / review.
- **Detect:** `rg -n 'https?://[0-9]{1,3}(\.[0-9]{1,3}){3}' -t ts -t js -t json .`.
- **Violation:** IPv4 literals in production endpoints.

### I9. Device compatibility (iPad, Mac, Vision Pro, iPhone Duo)

- **Guidelines:** 2.4.1; App Review Help "Test your app on compatible devices" (iPhone apps
  run on iPad in compatibility mode and reviewers test on real devices; removing a
  destination does not stop iPad downloads).
- **Severity / category:** MEDIUM / review (raise to HIGH with crash evidence).
- **Detect:** `supportsTablet`, `requireFullScreen`, orientation settings,
  `UIRequiredDeviceCapabilities`; `rg -n 'Dimensions\.get\(' -t ts -t js .` at module scope
  (never updates on size changes); hardware APIs without availability checks (HealthKit on
  iPad, camera, NFC).
- **Violation:** module-scope dimension constants and fixed phone widths with
  `supportsTablet: true`; crashes when optional hardware is missing; using
  `UIRequiredDeviceCapabilities` as a distribution preference.
- **Note:** iPhone Duo shipped October 23, 2026; its screenshot requirement date is in
  `facts.json` `deadlines`. Layouts should respond to window size changes.

### I10. Secrets and data security

- **Guidelines:** 1.6 (appropriate security measures; prevent unauthorized access).
- **Severity / category:** BLOCKER / security for server-power secrets; MEDIUM / hygiene for
  storage issues.
- **Detect:** D:secrets.
- **Violation (BLOCKER):** server secrets in the client: `sk_live_`, service-account JSON,
  JWT signing secrets, AI provider keys, MusicKit or APNs `.p8` private keys, admin tokens,
  and any secret in `EXPO_PUBLIC_*` variables (Expo inlines them into the shipped JS).
- **Violation (MEDIUM):** auth tokens in AsyncStorage instead of Keychain
  (expo-secure-store); `NSAllowsArbitraryLoads` true without need; plaintext http endpoints.
- **Not a violation:** publishable keys designed for clients (see Guards).
- **Fix:** move secrets server-side and rotate them (needs-user).

### I11. Production logging

- **Guidelines:** 1.6 when tokens or PII are logged; otherwise hygiene.
- **Severity / category:** MEDIUM / hygiene (security when secrets or PII are printed).
- **Detect:** `rg -n 'console\.(log|warn|debug|info)' -t ts -t js -g '!**/*test*' -g '!**/__tests__/**' .`.
  A `transform-remove-console` babel plugin in production downgrades to informational.

### I12. Other-platform references

- **Guidelines:** 2.3.10 (no names, icons, or imagery of other mobile platforms or
  alternative app marketplaces in the app or metadata).
- **Severity / category:** MEDIUM / review.
- **Detect:** `rg -n 'Android|Google Play|Play Store|Galaxy Store|Samsung' -t ts -t js .`.
- **Not a violation:** `Platform.OS === 'android'` branches; strings never rendered on iOS.

### I13. Export compliance key

- **Guidelines:** ASC export compliance.
- **Severity / category:** MEDIUM / upload (friction).
- **Detect:** `ITSAppUsesNonExemptEncryption` in D:native-config.
- **Rule:** `false` is correct only when the app uses exempt encryption (HTTPS, standard OS
  crypto); custom or proprietary cryptography needs `true` and documentation.

### I14. Developer contact information

- **Guidelines:** 1.5.
- **Severity / category:** MEDIUM / review (BLOCKER inside E1 for UGC apps).
- **Requirement:** an easy in-app way to contact the developer, matching the Support URL.

### I15. First-launch downloads, restarts, system behavior

- **Guidelines:** 4.2.3(ii), 2.4.4, 2.5.9, 2.5.15.
- **Severity / category:** MEDIUM / review.
- **Violation:** large required downloads on first launch without disclosing size and asking;
  asking users to restart the device or change unrelated settings; blocking links out to
  other apps; file pickers that exclude Files or iCloud documents.

---

## J. design (4.0, 4.1, 4.2, 4.3, 4.7)

### J1. Minimum functionality: thin WebView wrappers

- **Guidelines:** 4.2, 4.2.2.
- **Severity / category:** HIGH / review.
- **Detect:** `rg -n '<WebView' -t ts -t js -l .`; judge what share of the core experience is
  web content.
- **Violation:** the home screen is `<WebView source={{ uri: 'https://example.com' }} />`;
  the app is mainly marketing, links, or aggregated web clippings.
- **Not a violation:** WebViews for checkout of physical goods, OAuth, help articles, or
  embedded documents.

### J2. Templates, white-label apps, duplicates

- **Guidelines:** 4.2.6, 4.3(a), 4.3(b).
- **Severity / category:** HIGH / review (judgment).
- **Detect:** multiple production bundle identifiers or brand variants in app config or
  eas.json; app-builder or template signatures.
- **Violation:** one codebase shipped as many near-identical apps (per city, team, or
  client) by the same account; template apps submitted on behalf of clients; an app in a
  saturated category (dating, flashlight, wallpaper, simple timers, fortune telling) with no
  meaningfully different experience.

### J3. Copycats and other developers' brands

- **Guidelines:** 4.1(a)-(c) (4.1(c) new November 13, 2025), 5.2.1.
- **Severity / category:** MEDIUM / review.
- **Detect:** app `name` and icon in app config; in-app use of other brands' names or logos.
- **Violation:** another developer's icon, brand, or product name in the app's icon or name
  without approval; UI cloned from a popular app.
- **Not a violation:** factual integration mentions ("Works with Apple Health") that follow
  the brand owner's guidelines.

### J4. Mini apps, mini games, chatbots, plug-ins, streamed games, emulators

- **Guidelines:** 4.7, 4.7.1-4.7.5 (HTML5 and JavaScript mini apps in scope since November
  13, 2025).
- **Severity / category:** HIGH / review.
- **Applies when:** the app loads third-party interactive software not embedded in the binary.
- **Detect:** D:webview-bridges.
- **Violation:** the hosted software skips 5.1 privacy rules, 1.2 filtering, reporting, and
  blocking, or 3.1 IAP rules (4.7.1); native APIs exposed to it through a bridge
  (`onMessage` handlers, `injectedJavaScript`, message handlers calling native modules)
  without Apple's permission (4.7.2); data or permissions passed to it without per-instance
  consent (4.7.3); no index of offered software with universal links (4.7.4); no way to
  identify content above the app's age rating and no verified or declared age gate
  (4.7.5).

### J5. General minimum functionality

- **Guidelines:** 4.2, 4.2.1, 4.2.3(i).
- **Severity / category:** MEDIUM / review (judgment).
- **Violation:** an app that is only a song, book, or single static screen; AR that merely
  drops a model; requiring another app to be installed to function.

---

## False-positive guards

Apply all of these before reporting. A verifier refutes a finding by citing one with
concrete evidence.

1. **Shipped code only.** Ignore code behind `__DEV__`, non-production EAS profiles, test
   files, Storybook, mocks, scripts, and Android-only branches. In CNG projects ignore a
   gitignored `ios/` directory entirely: it is a stale local prebuild, not what EAS builds.
2. **Publishable keys are designed to ship:** Stripe `pk_live_`, Firebase web `AIza` keys,
   RevenueCat public SDK keys, PostHog project keys, Sentry DSNs, Google OAuth client IDs,
   Mapbox public `pk.` tokens.
3. **Physical goods and real-world services** must not use IAP (3.1.3(e)); live one-to-one
   services may skip IAP (3.1.3(d)).
4. **US storefront link-outs** gated on the StoreKit storefront are permitted (3.1.1(a),
   3.1.3).
5. **Reader apps** (3.1.3(a)) may give access to previously purchased content without IAP.
6. **Account deletion web step:** a direct link to the exact deletion page is allowed.
7. **First-party analytics** that are not shared for advertising are not tracking; IDFV for
   same-developer analytics is not tracking.
8. **Apple's own URLs:** `apps.apple.com/account/subscriptions`, `?action=write-review`
   links, `showManageSubscriptions`, `beginRefundRequest`.
9. **Content visible only to its author** is not UGC under 1.2. Friends-only or private
   group content seen by other users is.
10. **On-device AI** (Foundation Models, Core ML) is not third-party AI under 5.1.2(i).
11. **Write-only photo access** for saving images is minimal access, not a 5.1.1(iii) issue.
12. **Remote paywall templates** (RevenueCat Paywalls, Superwall): layout is configured in a
    dashboard; mark layout items needs-user rather than "missing".
13. **Kill switches and staged rollouts** of reviewed, reachable, documented features are not
    2.5.19 violations.
14. **Guideline reading too broad:** if the guideline text requires something narrower than
    the finding claims, the finding is refuted or downgraded.

## Current guideline numbering reference

Use these numbers. They reflect the October 16, 2026 text.

| Topic | Guideline |
|---|---|
| UGC moderation (filter, report, block, contact) | 1.2 |
| Creator content age restriction | 1.2.1(a) |
| Kids Category | 1.3, 5.1.4 |
| Medical accuracy and claims | 1.4.1 |
| Risky challenges | 1.4.5 |
| Developer contact info | 1.5 |
| Data security | 1.6 |
| Completeness, demo accounts, backend live | 2.1(a) |
| IAP visible and functional for review | 2.1(b) |
| Review notes describe new features | 2.3.1(a) |
| Age rating answers | 2.3.6 |
| "For Kids" wording reserved | 2.3.8 |
| Other platforms and marketplaces | 2.3.10 |
| What's New text | 2.3.12 |
| Creative assets | 2.3.14 |
| iPad and device compatibility | 2.4.1 |
| Public APIs, HealthKit purpose, current OS | 2.5.1 |
| Downloaded code | 2.5.2 |
| Background modes | 2.5.4 |
| IPv6-only networks | 2.5.5 |
| Facial authentication | 2.5.13 |
| Recording consent and indicator | 2.5.14 |
| Widgets, extensions, App Clips | 2.5.16 |
| Advertising | 2.5.18 |
| Hidden, dormant, undocumented features | 2.5.19 |
| In-App Purchase | 3.1.1 |
| Link to other purchase methods (entitlements, US) | 3.1.1(a) |
| Subscriptions: uses, upgrades, information | 3.1.2(a), (b), (c) |
| Other purchase methods (reader, P2P, physical) | 3.1.3(a)-(g) |
| Cryptocurrencies | 3.1.5 |
| P2P monetary gifts | 3.2.1(vii) |
| No forced ratings or store actions | 3.2.2(x) |
| Copycats; other developers' brands | 4.1(a)-(c) |
| Minimum functionality | 4.2 |
| Spam, saturated categories | 4.3(a), (b) |
| Apple Music | 4.5.2 |
| Push and Live Activities spam | 4.5.3 |
| Push notifications | 4.5.4 |
| Mini apps and embedded software | 4.7, 4.7.1-4.7.5 |
| Login services | 4.8 |
| Apple Pay | 4.9 |
| Monetizing built-in capabilities | 4.10 |
| Privacy policy | 5.1.1(i) |
| Consent and purpose strings | 5.1.1(ii) |
| Data minimization | 5.1.1(iii) |
| Respect permissions, no manipulation | 5.1.1(iv) |
| Account sign-in and deletion | 5.1.1(v) |
| SafariViewController | 5.1.1(vii) |
| Regulated fields | 5.1.1(ix) |
| Optional contact info | 5.1.1(x) |
| Data sharing, third-party AI, ATT | 5.1.2(i) |
| Sensitive API data limits | 5.1.2(vi) |
| Health and health research | 5.1.3 |
| Location | 5.1.5 |
| Third-party services; media downloading | 5.2.2, 5.2.3 |
| Apple products, previews, Activity rings | 5.2.5 |
| Sweepstakes and contests | 5.3.1, 5.3.2 |
| Developer Code of Conduct; manipulation | 5.6 |
| Ratings prompts | 5.6.1 |

Retired or moved: 2.3.1 no longer holds the hidden-features rule (now 2.5.19); 2.5.10 was
deleted (November 13, 2025); 3.1.5 is cryptocurrencies, not physical goods; IPv6 is 2.5.5,
not 2.1; purpose strings are 5.1.1(ii), not 5.1.1(i); 4.8 no longer names Sign in with Apple
as mandatory, it requires an equivalent privacy-preserving login option.
