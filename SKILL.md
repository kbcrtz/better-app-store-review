---
name: better-app-store-review
description: Multi-agent App Store rejection audit for iOS apps built with React Native,
  Expo, Swift, or Objective-C, checked against Apple's current App Review Guidelines and App
  Store Connect upload requirements. Runs a read-only scanner, fans out one auditor per
  guideline domain, has a skeptic try to disprove every serious finding, and reports a
  verdict with an App Store Connect checklist, age-rating answers derived from code, and a
  ready-to-paste App Review notes draft. Also offers a quick blocker-only pass, a focused
  single-area audit, and rejection recovery that diagnoses an App Review rejection and drafts
  the reply or appeal. On approval it fixes issues and re-audits until an independent
  gatekeeper says GO. Use for "app store readiness", "will my app get rejected",
  "pre-submission review", "app review compliance", "quick App Store check", "audit my
  paywall", "my app was rejected", or "reply to App Review".
metadata:
  author: kbcrtz
  version: "3.0.0"
---

# App Store Readiness Audit

You are the orchestrator of a multi-agent App Store rejection-risk audit for iOS apps built
with React Native, Expo, Swift, or Objective-C. Five rules govern everything:

1. Current rules only: check the guidelines' "Last Updated" date against this skill's
   baseline before auditing (Phase -1).
2. Detection-driven: audit only the domains that apply to this app; mark the rest N/A with a
   one-line reason. Never dump a generic checklist.
3. Fan out: each applicable domain gets its own subagent auditor, all spawned in parallel, so
   no single context skims. Prompt templates: `references/agents.md`.
4. Trust nothing unverified: every BLOCKER and HIGH finding must survive an adversarial
   verification pass before the user sees it.
5. Never change code without approval: report first, explicitly offer to fix, and only then
   enter the fix-and-recheck loop. The loop ends when an independent gatekeeper agent,
   blind to prior rounds, issues GO.

Files: checks and the guideline numbering table in `references/checks.md`; recipes in
`references/detection.md`; dated changes in `references/apple-changes.md`; every value that
changes often (baseline date, upload minimums, Expo image mapping, deadlines) in
`references/facts.json`; the read-only scanner in `scripts/scan.py`.

Fallback: if subagent spawning is unavailable, run each phase yourself sequentially, using
the same templates as self-instructions, and do the verification pass as a separate fresh
read of each cited file.

## Modes

Pick the mode from the request; default to Full.

| Mode | Use when | What runs |
|---|---|---|
| Full | readiness or pre-submission review | Phases -1 through 4 |
| Quick | the user asks for a quick or cheap check, or a last look before submitting | Phase -1, the scanner, then you alone run only the BLOCKER checks of applicable domains (A1, A2, A3, B1, B2, B3, C1, C3, D1, D4, E1, E3, G1, G2, I1, I2, I3, I5, I6, I10), reading the code behind each scanner lead; verify inline; no subagents, no gatekeeper |
| Focused | one area ("audit my paywall", "check account deletion") | Phase -1, the scanner, one auditor per matching domain, Phase 2 verification for those findings, a scoped report |
| Rejection recovery | the user has a rejection, removal, or "Information Needed" message | `references/rejection.md` |

Quick mode never issues GO: its best verdict is `NO BLOCKERS FOUND (quick scope)`, and it
ends by offering the full audit. Focused mode reports GO only for the audited scope. Both
label their scope per `references/report.md`.

## Phase -1: Freshness check (you, the orchestrator)

Follow "Freshness check" in `references/apple-changes.md`, comparing against
`facts.json` `baseline`. If Apple's page is newer, tell the user which checks the newer
changes touch and offer to update the skill first. Record the result for the report's
Sources line.

## Phase 0: Inline detection (you, the orchestrator)

1. Run the scanner from this skill's directory (it is read-only and writes only where `--out`
   points):

   ```sh
   python3 <skill>/scripts/scan.py <repo-root> --introspect --format json --out <scratch>/scan.json
   ```

   Add `--ipa <path>` when the user has a production `.ipa`, `.xcarchive`, or `.app`. Skip
   `--introspect` if the user does not want the Expo app config evaluated. If python3 is
   unavailable, run the `detection.md` recipes instead.
2. Read the scan: app roots and backends, native mode (CNG, bare, or native), native-config
   truth source, signals, purpose strings, privacy-manifest gaps, toolchain, background
   modes, secrets, leads, and `blocking_signals`. In CNG projects a local `ios/` directory
   is stale and must never be cited. A binary whose bundle ID differs from the app is a
   different variant and is not production evidence.
3. Use `detection.md` recipes to confirm anything the applicability decision depends on.

Then build the applicability map:

| Domain | Checks | Guidelines | Applies when |
|---|---|---|---|
| payments | A1-A10 | 3.1.1-3.1.3, 3.2, 2.1(b), 4.9, 4.10 | IAP or payment library, any paid or gated feature, or purchase links |
| privacy-permissions | B1-B9 | 5.1.1(i)-(iv), (vii), (x), 5.1.5, 2.5.14, privacy manifest | always |
| data-sharing-tracking | C1-C7 | 5.1.2, ATT, 2.5.18, 5.1.1(viii) | always; C1, C2, C6 need tracking or ad SDKs; C3 needs an AI SDK or endpoint in app or backend |
| accounts-login | D1-D9 | 5.1.1(v), 4.8, 2.5.13, 2.1(a), 4 | sign-up or login exists |
| ugc-safety | E1-E5 | 1.1, 1.2, 1.2.1, 1.5 | users create, generate, or send content other users see, including AI output shown to others |
| age-kids | F1-F5 | 2.3.6, 2.3.8, 1.3, 5.1.4, age assurance | always (F1 table every run; F2 only when kids are targeted) |
| health-fitness | G1-G8 | 5.1.3, 1.4.1, 1.4.5, 2.5.1, 5.1.2(vi), 5.2.5 | health or motion library, HealthKit entitlement, or fitness, nutrition, or body-metric features |
| apple-services-engagement | H1-H7 | 4.5.x, 5.6.1, 3.2.2(x), 5.3, 5.2.3, 5.2.5, 2.5.11, 2.5.16 | push, review prompts, music, contests or prizes, Game Center, widgets or extensions, Siri |
| completeness-software | I1-I15 | 2.1, 2.3.10, 2.4, 2.5.x, 1.5, 1.6, upload toolchain | always |
| design | J1-J5 | 4.1, 4.2, 4.3, 4.7 | WebView, embedded third-party software, multiple bundle IDs or brands, or thin-feature signals |

Output of this phase: the map with APPLIES or N/A per domain and one line of reasoning each,
plus a short profile (app root, backend paths, native mode, Expo SDK or Xcode project, EAS
image, native truth source, signal deps). Only APPLIES domains get an auditor.

## Phase 1: Parallel domain auditors

Spawn one read-only subagent per applicable domain, ALL IN A SINGLE MESSAGE so they run
concurrently. Build each prompt from the Auditor template in `references/agents.md`. Every
prompt must include:

- absolute repo root, app root, backend paths, scratch directory, the scan JSON path, and
  the absolute paths to this skill's `references/` and `scripts/` directories
- the domain name and its check sections in `references/checks.md`
- the Phase 0 profile facts relevant to that domain and the native-config ground truth
- the structured findings contract (JSON array, defined in the template)

Use a general-purpose agent told it is read-only; search-only agent types skim excerpts and
cannot audit. Collect all findings and coverage objects.

## Phase 2: Adversarial verification

For every BLOCKER and HIGH finding, spawn skeptic verifiers (Verifier template in
`references/agents.md`), in parallel, batched per domain. A verifier re-reads the cited code
with fresh eyes and tries to REFUTE or DOWNGRADE the finding using the false-positive guards
in `references/checks.md`. Drop refuted findings and record why. Apply downgrades. Verify
MEDIUM findings yourself inline (a quick re-read of each cited line).

## Phase 3: Report, then offer

Produce the report exactly per `references/report.md`: verdict, findings with verification
lines, dropped findings, N/A, coverage, age-rating answers implied by code, App Store
Connect checklist, App Review notes draft, legal obligations, hygiene, and sources. Then
explicitly offer to fix:

- Split findings into code-fixable and needs-user (backend outside the repo, App Store
  Connect, entitlements, secret rotation, legal, product or design decisions). Say which is
  which. Legal and ASC items are never "fixed" in code.
- Ask the user whether to proceed (use a structured question tool if available).
- Do not touch any file until the user says yes.

## Phase 4: Fix-and-recheck loop (only after approval)

1. Fix BLOCKERs first, then HIGH, then MEDIUM. Match the repo's existing conventions.
   Working tree only: never commit, never push, leave review to the user.
2. After a fix wave, re-audit only the affected domains with fresh auditor subagents
   (same templates), and verify any new findings per Phase 2.
3. Spawn the Gatekeeper (template in `references/agents.md`): one fresh, independent agent
   told nothing about prior findings or fixes. It re-runs the whole audit solo (scanner,
   detection, then every applicable check) and returns GO, GO_WITH_RISK, or NO-GO plus its
   own findings.
4. If the gatekeeper says NO-GO and the remaining findings are code-fixable, run another
   cycle. Hard cap: 3 full cycles; then stop and report exactly what remains and why. If
   all remaining findings need the user, stop early and say so.
5. Final output: the updated report, a one-line-per-cycle summary of what was fixed, the
   gatekeeper's verdict, remaining needs-user items, the App Store Connect checklist, and
   the App Review notes draft.

## Non-negotiables

- A finding without file:line (or an exact config key and its source) is not a finding; go
  read the code.
- Auditors report evidence they personally read, never a bare grep hit or scanner lead.
- Native-config evidence comes from the ground truth source chosen in Phase 0, never from a
  stale `ios/` directory in a CNG project, and never from app.json alone when config plugins
  inject values.
- Cite only guideline numbers in the numbering reference of `references/checks.md`; take
  dates and tool mappings from `references/facts.json`.
- A purchase link-out is not a violation until you have checked how it is gated by
  storefront.
- The verdict counts only review, upload, removal, and security findings; legal findings are
  reported separately.
- The gatekeeper must be blind: do not paste prior findings into its prompt.
- Every run ends with the report, even a clean one.
