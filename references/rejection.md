# Rejection recovery

Use this mode when the user already has a rejection, removal, or "Information Needed"
message from App Review. The goal is the shortest honest path back to approval: find the
real cause in code or metadata, pick the right response channel, and draft the exact words.

Sources: App Review Guidelines "After You Submit", and App Review Help pages "Contact App
Review", "Appeal to the App Review Board", "Accept Bug Fix Submission offers", "Request an
expedited review", and "Request a one-on-one App Review appointment" (read November 11, 2026).

## 1. Capture the message verbatim

Ask for the full text from App Store Connect, not a summary. Record for each cited issue:

- the guideline header exactly as written (for example
  `Guideline 5.1.1(v) - Data Collection and Storage`); a message can cite several
- the reviewer's observation sentences and any "Next Steps" text
- the review environment: submission ID, version and build reviewed, device and OS
  (for example "iPad Air (5th generation), iPadOS 26.4")
- attachments: screenshots (ask the user to describe or share them) and crash logs
- whether the message begins with "Bug Fix Submissions: The issues we've identified below are
  eligible to be resolved on your next update."
- whether this is a repeat rejection for the same guideline (repeats lengthen review)

Never paraphrase Apple's words in the drafts you produce; quote them.

## 2. Map each cited issue to checks

Use the numbering reference in `checks.md`. Note moved numbers: hidden-feature messages that
cite 2.3.1 map to I3 (now 2.5.19). Typical reviewer wording and where to look:

| Reviewer wording (paraphrased) | Guideline | Checks |
|---|---|---|
| Unable to locate or purchase the in-app purchases | 2.1(b) | A9 (empty offerings, products not submitted, Paid Apps Agreement) |
| Information needed: demo account, feature location, hardware | 2.1 | D9, review notes |
| Crash or bug, often on iPad or a specific OS | 2.1 | I2, I9, G4 (HealthKit on iPad) |
| Purpose string does not explain the use | 5.1.1(ii) | B2 (read the introspected or binary Info.plist) |
| Permission request preceded by a custom screen or "Allow" button | 5.1.1(iv) | B4 |
| Registration required for non-account features | 5.1.1(v) | D6 |
| No account deletion, or deletion requires contacting support | 5.1.1(v) | D1 |
| Third-party login without an equivalent option | 4.8 | D4 |
| Asks for name or email after Sign in with Apple | 4 | D5 |
| Purchase buttons or links to other payment methods | 3.1.1, 3.1.1(a) | A1 (check storefront gating first) |
| Subscription terms, price prominence, missing Terms of Use | 3.1.2 | A2, ASC metadata |
| Tracking without ATT, or ATT prompt not found | 5.1.2, 2.1 | C1, C2 |
| Personal data shared with third-party AI | 5.1.2(i) | C3 |
| Custom review prompt | 5.6.1 | H2 |
| UGC without filter, report, block, or EULA | 1.2 | E1 |
| Hidden or undocumented features, behavior changed after review | 2.5.19 | I3, I4 |
| HealthKit not visible in the app or description | 2.5.1 | G4 |
| Background mode not used | 2.5.4 | I7 |
| Spam or duplicate apps | 4.3(a), 4.3(b) | J2 (mostly a product argument, not code) |
| Minimum functionality, web wrapper | 4.2 | J1, J5 |
| Screenshots, metadata, other platforms | 2.3.x, 2.3.10 | ASC checklist, I12 |

If no check matches, read the cited guideline text in Apple's current guidelines and reason
from it directly.

## 3. Find the cause

For each cited issue, run the mapped checks as a focused audit (Focused mode in SKILL.md)
with the reviewer's observation as the hypothesis to confirm or refute:

- Reproduce the reviewer's path on the reviewer's device class. Many 2.1 crashes and 4.0
  layout rejections happen only on iPad in compatibility mode.
- For crash logs: symbolicate against the exact build (Xcode Organizer, or the dSYM from the
  EAS build artifacts), read the exception type and the crashing thread, then find the code.
- Check whether the cause is in code, in App Store Connect, or in a server that was down or
  misconfigured during review (2.1 requires backend services to be live).
- Confirm whether the issue still exists at HEAD; it may be fixed already, or the reviewed
  build may differ from HEAD.

## 4. Choose the response for each issue

| Response | When | Channel |
|---|---|---|
| CHANGE_BUILD | The cause is in code or the binary | Fix (Phase 4 loop with approval), new build, resubmit, explain the change in the reply |
| CHANGE_METADATA | The cause is only in App Store Connect (screenshots, description, privacy answers, age rating, review notes, demo account, IAP setup) | Edit ASC, then reply and resubmit without a new build |
| EXPLAIN | The app already complies and the reviewer missed or misread something, or App Review asked for information | Reply to App Review in App Store Connect with exact steps; no new build |
| DEFER | The message carries the Bug Fix Submissions eligibility note (updates to already-approved apps only, never legal or safety issues) | Reply asking to approve this submission and commit to resolving the issues in the next update; do not resubmit. Deferred issues cannot be deferred again |
| APPEAL | The app complies, a reply did not resolve it, and you can show point by point how it meets the guideline | App Review Board appeal form, one appeal per app covering every cited guideline |
| ASK | You are unsure how a guideline applies | Reply with a specific question, or request a call (include time zone), or book a one-on-one App Review appointment (informational only; it never preapproves) |

Rules:
- Reply before appealing. Apple asks developers to clarify through the rejection message
  first and to appeal only if that fails.
- Never appeal a request for information, and never appeal after already resubmitting a fix.
- Do not resubmit an unchanged binary for a CHANGE_BUILD issue.
- Expedited review is for genuine urgency (critical bug, dated event) and is requested after
  submitting, with the reason in the review notes. It is not an appeal channel.
- Address every cited guideline in one reply.

## 5. Draft the outputs

Produce, in this order:

1. **Diagnosis table**: cited guideline, root cause with file:line or ASC field, response
   type, and the evidence (CONFIRMED by verification, or why it could not be confirmed).
2. **Reply to App Review** (for EXPLAIN, CHANGE_*, DEFER):

   ```
   Hello App Review team,

   Thank you for reviewing <App name> <version> (<build>).

   Guideline <number>: "<quote of the reviewer's observation>"
   <What we changed in build <n>, or where the feature is and how to reach it:>
   1. <step>
   2. <step>
   <Demo account or code if relevant: see App Review Information; code <123456>.>

   <Repeat per guideline.>

   We have <resubmitted build <n> / updated the App Store Connect metadata / not resubmitted,
   per the Bug Fix Submission offer>. Please let us know if anything else is needed.
   ```

   Keep it factual and specific; no arguments, no promises the code does not keep (5.6).
3. **Appeal text** (APPEAL only): cite each guideline, then explain point by point how the
   app satisfies it with concrete evidence (screens, flows, documents). Leave out business
   impact; Apple's own example of an incomplete appeal is "This app is important to my
   business and shouldn't have been rejected."
4. **Updated App Review notes** (see report.md "App Review notes draft"), adding what the
   reviewer could not find.
5. **Fix list** for CHANGE_BUILD items, ready for the Phase 4 loop with the user's approval.
6. **Prevention**: the checks that would have caught this, so the next full audit includes
   them.
