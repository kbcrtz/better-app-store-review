# Subagent prompt templates

Three templates. Fill every `{PLACEHOLDER}` before spawning; never send a template raw.
`{REFS}` is the absolute path to this skill's `references/` directory and `{SCRIPTS}` its
`scripts/` directory. `{ROOT}` is the absolute repo root, `{APP}` the absolute app root (may
equal `{ROOT}`), `{BACKEND}` the absolute backend paths or "none in repo", `{SCRATCH}` a
scratch directory outside the repo, and `{SCAN_JSON}` the Phase 0 scanner output.

Agent type: use a general-purpose agent and tell it it is read-only. Avoid search-only agent
types that read excerpts: auditors must read whole implicated files. Run every auditor and
verifier in the background in parallel, then wait for all of them.

## Findings contract (shared)

Auditors and the gatekeeper return ONLY a JSON array (empty `[]` if nothing found):

```json
[
  {
    "guideline": "5.1.2(i)",
    "severity": "BLOCKER",
    "category": "review",
    "title": "Fridge photos sent to a third-party AI without explicit permission",
    "file": "src/screens/ScanFridge.tsx",
    "line": 112,
    "evidence": "uploadPhoto(uri).then(() => api.post('/ai/ingredients', { key }))  // server forwards to the AI provider",
    "why": "5.1.2(i) requires clear disclosure and explicit permission before personal data is shared with third-party AI",
    "fix": "Show a one-time disclosure naming the provider and the data, require opt-in, store the choice, add a settings toggle",
    "fixable_from_code": true,
    "scope": "all storefronts"
  }
]
```

Fields:
- `severity`: BLOCKER, HIGH, or MEDIUM (definitions in checks.md).
- `category`: review, upload, removal, security, legal, or hygiene (definitions in
  checks.md). Legal items never affect the verdict.
- `fixable_from_code`: false when the fix needs the user (backend outside the repo, App Store
  Connect, secret rotation, entitlements, legal decision, product decision).
- `scope`: optional; storefronts, regions, or devices the finding is limited to.
- For config findings, `file` is the config path (for example `app.config.js`, or
  "introspected Info.plist" or "IPA Info.plist") and `line` is the key's line or 0.

## Auditor template

```
You are auditing exactly ONE domain of a React Native / Expo iOS app for App Store
rejection risk. You are read-only: never edit, write inside the repo, commit, or run
state-changing commands. You may write scratch files only under {SCRATCH}.

Domain: {DOMAIN}
Check sections you own: {CHECKS_SECTIONS} in {REFS}/checks.md
Guidelines you own: {GUIDELINE_LIST}
Repo root: {ROOT}
App root: {APP}
Backend: {BACKEND}
Phase 0 profile: {PROFILE_FACTS}
Native-config ground truth: {NATIVE_TRUTH}
  (introspected Info.plist and entitlements, or IPA facts, or "bare: read ios/". In a CNG
  project the local ios/ directory is stale; never cite it.)
Scanner output: {SCAN_JSON}
  (read the parts for your domain: purpose_strings, privacy_manifest, toolchain,
  background_modes, signals, and the leads whose "checks" include your check IDs. Leads are
  starting points, never findings.)
Volatile facts (dates, tool mappings): {REFS}/facts.json

Procedure:
1. Read your sections of {REFS}/checks.md, the "False-positive guards" and the "Current
   guideline numbering reference" at the end of that file, and the recipes in
   {REFS}/detection.md that your checks reference. The checks are your floor, not your
   ceiling: report any violation of your guidelines that has no listed check.
2. Run the recipes, then READ every implicated file with surrounding context. A grep hit is
   a lead, not evidence. When data leaves the app (deletion, moderation, push, AI, analytics,
   Sign in with Apple), follow it into {BACKEND} and read the handler.
3. Apply every false-positive guard before reporting.
4. Be exhaustive: enumerate every surface relevant to your domain (every purchase screen,
   every permission, every UGC surface, every AI call, every push type) and include, as the
   LAST element of the array, one object {"coverage": ["surface: file", ...]} listing what
   you covered.
5. Cite only guideline numbers that appear in the numbering reference. Quote evidence you
   personally read.

Return ONLY the JSON array defined by this contract (findings, then the coverage object):
{FINDINGS_CONTRACT}
Nothing else in your final message.
```

## Verifier template

```
You are a skeptic reviewing one finding from a pre-submission App Store audit of the repo
at {ROOT} (app root {APP}, backend {BACKEND}). Your job is to try to REFUTE it. You are
read-only.

The finding:
{FINDING_JSON}

Procedure:
1. Read the cited file and at least 40 lines of surrounding context, plus any handler the
   finding depends on (backend endpoint, config plugin, SDK init).
2. Check the escape hatches in {REFS}/checks.md "False-positive guards", especially:
   - not shipped: __DEV__, non-production EAS profile, tests, Android-only, dead code, or a
     gitignored ios/ directory in a CNG project;
   - storefront scoping: US-only purchase links gated on the StoreKit storefront; regional
     entitlements;
   - payment exemptions: physical goods (3.1.3(e)), live one-to-one services (3.1.3(d)),
     reader apps (3.1.3(a));
   - account deletion: a direct link to the exact deletion page is allowed;
   - tracking: first-party analytics and IDFV are not tracking;
   - AI: on-device models are not third-party AI;
   - Apple URLs and APIs: subscription management, write-review links;
   - remote paywalls: layout configured in a dashboard.
3. Read the guideline text quoted in checks.md and ask whether the finding reads it too
   broadly for what this code actually does.
4. Check severity and category against the definitions in checks.md; you may downgrade.

Verdict rules: REFUTED requires concrete evidence (name the guard or the exact code path).
If the violation is real, or you cannot find concrete refuting evidence, return CONFIRMED;
an App Store rejection costs more than a reviewed finding.

Return ONLY this JSON:
{"verdict": "CONFIRMED" | "REFUTED" | "DOWNGRADED", "severity": "<final severity>",
 "reason": "one or two lines"}
```

## Gatekeeper template

The gatekeeper decides whether the codebase ships. Spawn it fresh and blind: no prior
findings, no list of fixes, no hints about what was changed.

```
You are the final gate before an App Store submission. Audit the React Native / Expo iOS
app at {ROOT} from scratch and decide if it is ready. You are read-only (scratch files only
under {SCRATCH}). You have no knowledge of any earlier audit and must not ask for one.

Procedure:
1. Run `python3 {SCRIPTS}/scan.py {ROOT} --introspect --format json --out {SCRATCH}/gate-scan.json`
   (add `--ipa <path>` if the user supplied a production build) and read it. Then read
   {REFS}/detection.md for anything the scanner does not cover: locate the app and backend,
   native mode (CNG, bare, or native), native-config ground truth, signal dependencies,
   toolchain. Decide which domains in {REFS}/checks.md apply.
2. Read {REFS}/checks.md in full and run EVERY applicable check yourself, reading the
   implicated code (and backend handlers) rather than only grepping. Apply the
   false-positive guards and cite only numbers from the numbering reference.
3. Judge severity and category per checks.md.

Return ONLY this JSON:
{
  "verdict": "GO" | "GO_WITH_RISK" | "NO-GO",
  "findings": <the JSON findings array per the contract below>,
  "not_applicable": ["domain: one-line reason", ...]
}
Verdict rules, counting only categories review, upload, removal, and security:
NO-GO if any BLOCKER exists. GO_WITH_RISK if no BLOCKER but at least one HIGH. GO only
when nothing above MEDIUM remains. Legal and hygiene findings are listed but never change
the verdict.
Findings contract:
{FINDINGS_CONTRACT}
```

## Orchestrator notes

- Spawn all Phase 1 auditors in one message so they run in parallel; same for verifier
  batches in Phase 2.
- With few signals, merge two small domains into one auditor (for example design with
  apple-services-engagement when there is no WebView and no MusicKit). Never merge payments,
  privacy-permissions, accounts-login, or ugc-safety with anything.
- Deduplicate findings across auditors by (guideline, file, line) before verification;
  domains overlap on purpose (health data flows appear in health-fitness and
  data-sharing-tracking).
- Strip the trailing coverage object before verification; use it in the report's coverage
  line and to spot domains that skipped surfaces.
- If an agent returns malformed JSON, extract what you can; re-spawn only if unusable.
- The fix loop re-audits only affected domains, but the gatekeeper always audits everything.
- Fixes are applied by you, the orchestrator, in the main context (you hold the repo
  conventions and the user's constraints). Subagents never edit files unless the harness
  provides isolated worktrees.
