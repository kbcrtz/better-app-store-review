# Report format

The audit always ends with this report. Produce every section, in this order, even when a
section is empty (say "None found").

Quick mode and Focused mode use the same format with a scope line directly under the
verdict, for example `SCOPE: QUICK (blocker checks only; not a full audit)` or
`SCOPE: FOCUSED (payments)`. Sections outside that scope say "Not run in this mode".

## Structure

1. **Verdict** (first line). Count only findings whose category is review, upload, removal,
   or security:
   - `NO-GO (n blockers)` when any BLOCKER exists.
   - `GO WITH RISK` when no BLOCKER but at least one HIGH exists.
   - `GO` when only MEDIUM or nothing remains.

2. **Findings**, grouped BLOCKER, then HIGH, then MEDIUM. Legal and hygiene findings go in
   their own sections below, not here. Each finding:

   ```
   [GUIDELINE #] short title  (category; scope if limited)
   file:line (or "config: <source> <key>")
   Evidence: the offending snippet or setting, quoted
   Why it's rejected: one line tying the evidence to the guideline text
   Fix: concrete action (mark "needs user" if not fixable from code)
   Verification: CONFIRMED or DOWNGRADED (skeptic could not refute) for BLOCKER and HIGH
   ```

   After the findings, one line per DROPPED finding:
   `Dropped: [guideline] title (refuted: reason)`. This proves verification ran.

3. **Not applicable**: every domain skipped in Phase 0, one line of reason each.

4. **Coverage**: one line per domain listing the surfaces its auditor enumerated (from the
   coverage objects). A domain with no surfaces listed is a gap to call out.

5. **Age rating answers implied by code**: a table with one row per capability in checks.md
   F1, the answer the code implies (Yes, No, Frequent, Infrequent), and the evidence file.
   End with the minimum rating these answers force, for example "Social Media: Yes forces
   13+ unless social features are disabled for under-13 users via the Declared Age Range
   API". This is guidance for the ASC questionnaire, not a finding.

6. **Verify in App Store Connect** (out of code scope; a human checks these). Include the
   relevant subset. For any item tied to an entry in `facts.json` `deadlines`, add the date
   while it is still upcoming and drop it once it has passed (the requirement remains).
   - Privacy Policy URL in app metadata; Terms of Use (EULA) link in the description or the
     custom EULA field when subscriptions exist.
   - App Privacy answers match shipped SDKs, AI providers, and tracking status.
   - Review notes (2.3.1(a)): paste the draft from section 7.
   - Demo account that works through review; for subscriptions, an account with an expired
     subscription; any OTP or 2FA code given in advance; demo mode only with Apple approval.
   - Backend live during review; Paid Apps Agreement active; IAP products submitted with the
     build, with localized names, descriptions, and review screenshots.
   - What's New text lists significant changes (2.3.12).
   - Screenshots: majority show the app in use, current UI, no other-platform references;
     creative assets follow 2.3.14; device-specific screenshot requirements in `deadlines`.
   - Age rating questionnaire answered from section 5, including the social media capability
     question and the Shared Location and Dating and Relationships descriptors.
   - Regulated medical device status declared (Yes or No) when the primary or secondary
     category is Health and Fitness or Medical, or Medical or Treatment Information is
     "frequent".
   - EU Digital Services Act trader status (apps without it are removed from the EU store).
   - Export compliance answered; consistent with `ITSAppUsesNonExemptEncryption`.
   - App name 30 characters or fewer, no other developers' brands in name or icon (4.1(c)),
     no "for kids" wording outside the Kids Category.
   - Description mentions HealthKit integration when used (2.5.1); subscription period and
     pricing consistent with the paywall.
   - Entitlements requested in the developer portal match those in the build (for example
     StoreKit External Purchase Link, health records, MusicKit identifier).

7. **App Review notes draft**: text ready to paste into App Store Connect, App Review
   Information, Notes. Fill every line the audit can support with evidence; leave the rest
   as `[bracketed placeholders]` for the user. Never invent facts.

   ```
   About: [one sentence on what the app does and who it is for]. Business model:
   <free | auto-renewable subscription "<group or product names>" via In-App Purchase | ...>.
   Sign-in: demo account [username] / [password] <(has an expired subscription so the full
   purchase flow is reviewable)>. <Login code: [code], if the app uses SMS or email codes.>
   New or changed in this version:
   1. <feature>: <tab> > <screen> > <control>.
   Permissions: <each permission and the action that triggers it>.
   Tracking: <The app does not track users | The ATT prompt appears at <screen> before any
   tracking SDK starts>.
   External services: <sign-in providers>, <payments: Apple In-App Purchase via <SDK>>,
   <AI: <provider or "a third-party AI service">, receives <data>, after opt-in at <screen>>,
   <analytics>, <maps or other data providers>.
   Regional differences: <none | <feature> only on the <country> storefront, gated by the
   StoreKit storefront>.
   Feature flags: <none | <flag>: <state during review and what it controls>>.
   Tested on: [devices and OS versions].
   ```

8. **Legal and regional obligations (outside App Review)**: every finding with category legal,
   plus applicable items from checks.md F5 (Texas, Utah, Louisiana age assurance; Australia
   under-16 social media; 18+ download confirmation in Australia, Brazil, Singapore; Korea
   Sign in with Apple notification endpoint for Korea-based developers). State which Apple
   APIs the code already uses and end with "confirm obligations with counsel".

9. **Hygiene**: hygiene-category findings, one line each.

10. **Fix loop outcome** (only when the fix-and-recheck loop ran): one line per cycle
    ("Cycle 1: fixed 3 blockers, 1 high"), then the gatekeeper's independent verdict:

    ```
    GATEKEEPER: GO (independent full re-audit, 0 blockers, 0 high)
    ```

    If cycles were capped or findings remain that need the user, list them with why the
    loop could not resolve them.

11. **Sources**: one line with the guideline date checked, the skill baseline from
    `facts.json`, and the freshness check date. If the freshness check found a newer
    guideline date, say which checks may be stale.

## Example (filled in)

The app below is fictional: "Pantry", a recipe-sharing and meal-planning app.

```
VERDICT: NO-GO (2 blockers)

BLOCKER
[5.1.2(i)] Fridge photos sent to a third-party AI without explicit permission  (review)
src/screens/ScanFridge.tsx:112, server/src/ai/identifyIngredients.ts:58
Evidence: the scan button uploads the photo; identifyIngredients posts the image URL to
the AI provider's API. No disclosure or opt-in precedes the first scan.
Why it's rejected: 5.1.2(i) requires clear disclosure and explicit permission before
personal data is shared with third-party AI.
Fix: one-time disclosure sheet naming the provider and the data, explicit opt-in stored per
user, settings toggle, privacy policy and App Privacy updated, provider listed in review
notes.
Verification: CONFIRMED

[5.1.1(v)] Account deletion keeps recipes and photos  (review)
server/src/users/deleteAccount.ts:48
Evidence: deleteAccount() sets user.deleted = true; recipes, comments, and uploaded photos
remain stored and visible to other users.
Why it's rejected: deletion must remove the account and associated data, including
user-generated content shared with others, unless legally required.
Fix: hard-delete (or schedule hard-delete of) the user's rows and media; tell the user what
is retained and why if anything is.
Verification: CONFIRMED

HIGH
[4.5.4] Promotional pushes sent without an in-app marketing opt-in  (review)
server/src/jobs/promoPush.ts:40
Evidence: a weekly "Go Pro for 50% off" push goes to every device token; the app has no
marketing consent copy and no opt-out control.
Why it's rejected: push notifications for promotions require explicit opt-in through consent
language in the app UI and an in-app way to opt out.
Fix: add a "Promotions and offers" toggle (default off) with consent copy, store it, and
filter campaign sends on it.
Verification: CONFIRMED

MEDIUM
[2.3.10] "Google Play" mentioned in user-facing copy  (review)
src/components/ShareSheet.tsx:31
Evidence: "Also available on Google Play!"
Why it's rejected: the app must not reference other mobile platforms.
Fix: remove the line or gate it to Platform.OS === 'android'.

Dropped: [3.1.1] Web checkout link on Upgrade screen (refuted: link renders only when the
StoreKit storefront country is USA, permitted by 3.1.1(a))

NOT APPLICABLE
- data-sharing-tracking / ATT (C1, C2): no ad, attribution, or deep-linking SDK; analytics
  is first-party only.
- health-fitness: no health library, entitlement, or health data.
- design / mini apps (J4): react-native-webview not installed.

COVERAGE
- payments: Paywall.tsx, UpgradeSheet.tsx, Settings restore row
- ugc-safety: recipe posts, comments, profile bios, direct messages

AGE RATING ANSWERS IMPLIED BY CODE
| Capability | Implied answer | Evidence |
| User-Generated Content | Yes | src/screens/Feed.tsx |
| Social Media | Yes | likes and comments on a feed |
| Messaging and Chat | Yes | src/screens/Chat.tsx |
| Health or Wellness Topics | Infrequent | nutrition facts on recipes |
Minimum forced: 13+ (Social Media: Yes).

VERIFY IN APP STORE CONNECT (out of code scope)
- [ ] Privacy Policy URL and Terms of Use (EULA) link in metadata.
- [ ] App Privacy lists the AI provider and analytics SDK data.
- [ ] Review notes pasted from the draft below.
- [ ] Demo account with an expired subscription.
- [ ] Age rating: Social Media question answered Yes.

APP REVIEW NOTES DRAFT
About: [one sentence on what Pantry does and who it is for]. Business model: auto-renewable
subscription "Pantry Pro" (monthly, annual) via In-App Purchase.
Sign-in: demo account [username] / [password] (has an expired subscription so the full
purchase flow is reviewable).
New or changed in this version:
1. Fridge scan: Home > Scan > Take photo.
Permissions: Camera is requested when the user taps Take photo on the Scan screen.
Tracking: The app does not track users.
External services: Sign in with Apple and email login; payments: Apple In-App Purchase via
RevenueCat; AI: a third-party AI service receives the fridge photo after opt-in on the Scan
screen; analytics: first-party product analytics.
Regional differences: the Upgrade screen shows a web purchase link only on the United States
storefront, gated by the StoreKit storefront.
Feature flags: none.
Tested on: [devices and OS versions].

LEGAL AND REGIONAL OBLIGATIONS (outside App Review)
- Texas, Utah, Louisiana age assurance: no Declared Age Range API use found. Confirm
  obligations with counsel.

HYGIENE
- console.log of request bodies in src/api/client.ts:22 (no PII observed).

SOURCES
Checked against App Review Guidelines last updated October 16, 2026 (skill baseline October
16, 2026; freshness check run November 11, 2026).
```
