# Better App Store Review

**A multi-agent App Store rejection audit for iOS apps.** It doesn't hand your agent a checklist to skim. It splits the audit across specialist auditors, sends every serious finding to a skeptic that tries to disprove it, and only calls the app ready when an independent gatekeeper agrees.

[![MIT License](https://img.shields.io/badge/license-MIT-111318.svg)](LICENSE)
[![Apple guidelines baseline October 16, 2026](https://img.shields.io/badge/Apple%20guidelines-2026--10--16-3559D8.svg)](https://developer.apple.com/app-store/review/guidelines/)
![React Native, Expo, Swift](https://img.shields.io/badge/stack-React%20Native%20%7C%20Expo%20%7C%20Swift-61DAFB.svg)
![Version 3.0.0](https://img.shields.io/badge/version-3.0.0-555.svg)
[![skills.sh](https://skills.sh/b/kbcrtz/better-app-store-review)](https://skills.sh/kbcrtz/better-app-store-review)

**Current through:** Apple's App Review Guidelines, last updated [October 16, 2026](https://developer.apple.com/news/?id=92th7e5i). Checked against Apple's live page on November 11, 2026. Every audit re-checks Apple's date before it starts.

## Install

### skills.sh

```bash
npx skills add kbcrtz/better-app-store-review
```

### Claude Code plugin

```text
/plugin install better-app-store-review --marketplace kbcrtz/better-app-store-review
```

Or add the marketplace first:

```text
/plugin marketplace add kbcrtz/better-app-store-review
/plugin install better-app-store-review@better-app-store-review
```

### Codex plugin

```bash
codex plugin marketplace add kbcrtz/better-app-store-review
```

Then run `/plugins`, open the Better App Store Review marketplace, and install `better-app-store-review`.

### Manual

Clone the repository into `~/.claude/skills/better-app-store-review/` (all projects) or `.claude/skills/better-app-store-review/` (one project).

## Use it

Open your app's repository and ask:

```text
Will my app get rejected? Run a full App Store readiness audit.
```

| Mode | Ask for it like this | What you get |
|---|---|---|
| **Full** (default) | "Run a full App Store readiness audit." | Parallel auditors, skeptic verification, full report, optional fix loop with a blind gatekeeper |
| **Quick** | "Quick App Store check, blockers only." | One agent, blocker checks only, much cheaper; never claims GO, only "no blockers found" |
| **Focused** | "Audit my paywall." / "Check account deletion and Sign in with Apple." | One domain audited and verified in depth |
| **Rejection recovery** | "My app was rejected under 5.1.1. Here's the message." | Root cause in your code, the right response (new build, metadata fix, explanation, bug-fix deferral, or appeal), and the exact reply text |

Nothing in your repo changes until you approve the fixes.

## Why another App Store review skill?

Most App Store review skills are guideline indexes. They load the right section of Apple's rules and ask one agent to compare it against your code. That works for obvious problems, but a single context skims. One agent auditing payments, privacy, UGC, health, and toolchain at once misses things, and it reports its guesses as confidently as its facts.

This skill is built around three ideas:

1. **Fan out.** Each guideline domain gets its own auditor running in parallel. Each one covers a single domain in depth and must list every screen and flow it checked.
2. **Try to disprove everything.** Every BLOCKER and HIGH finding goes to a separate skeptic agent whose only job is to refute it, using a written list of known false positives. You see the findings that survived, plus a note on each one that was dropped and why.
3. **Ship on a blind second opinion.** After fixes, a fresh gatekeeper agent re-audits the whole app with no knowledge of the earlier findings or fixes. It returns GO, GO WITH RISK, or NO-GO.

## What makes it different

| | Typical review skill | Better App Store Review |
|---|---|---|
| Audit shape | One agent reads a rules file | 10 domain auditors in parallel, or a cheap Quick mode |
| False positives | Up to the reader | Skeptic verification for every BLOCKER and HIGH; dropped findings listed |
| Fixing | Suggestions | Optional fix loop, capped at 3 cycles, ending in a blind gatekeeper verdict |
| Deterministic pass | None, or a separate tool | Built-in read-only scanner feeds the auditors and runs in CI |
| Expo native config | Reads `app.json` | Reads `npx expo config --type introspect`, so plugin-injected purpose strings and background modes are caught |
| Stale `ios/` folders | Often treated as the source of truth | Detects Continuous Native Generation and never cites a gitignored `ios/` directory |
| Shipped binary | Not checked | Reads `.ipa`, `.xcarchive`, or `.app`: Info.plist, privacy manifest, entitlements, extensions, Xcode and SDK used; ignores builds from other variants |
| Your backend | Out of scope | Follows account deletion, moderation, push, AI calls, and Sign in with Apple token revocation into server code in the same repo |
| Guideline freshness | Whatever date it shipped with | Checks Apple's "Last Updated" date at the start of every run; volatile dates live in one file |
| Age rating | Not covered | Fills in the App Store Connect questionnaire answers from your code |
| Review notes | Not covered | Drafts the App Review notes from what the audit found |
| After a rejection | Not covered | Diagnoses the message and drafts the reply or appeal |
| Legal vs. review | Mixed together | Separates rejections, upload blockers, removal risk, security, and legal obligations; only real blockers affect the verdict |

## How it works

```
Phase -1  Freshness check     Compares Apple's live "Last Updated" date to the skill's baseline
Phase 0   Scan and detect     Read-only scanner, then targeted recipes: app, backend, native config, SDKs, toolchain
Phase 1   Domain auditors     One read-only agent per applicable domain, all in parallel
Phase 2   Verification        A skeptic agent tries to refute each BLOCKER and HIGH finding
Phase 3   Report              Verdict, findings, coverage, age rating, ASC checklist, review notes, legal
Phase 4   Fix loop (opt-in)   Fix, re-audit, blind gatekeeper; never commits or pushes
```

## Coverage

10 domains and 80 checks, each with the guideline text it enforces, how to detect it, what a violation looks like, what is explicitly allowed, and the fix.

| Domain | Guidelines | Highlights |
|---|---|---|
| Payments | 3.1.1-3.1.3, 3.2, 2.1(b), 4.9, 4.10 | Storefront-aware purchase links (US exemption, EU, Japan, Brazil); billed amount as the most prominent price; StoreKit-sourced prices; trial eligibility; restore |
| Privacy and permissions | 5.1.1, 5.1.5, 2.5.14 | Purpose strings from the real build, permission pre-prompt rules, photo picker minimization, privacy manifest aggregation across dependencies, session replay consent |
| Data sharing and tracking | 5.1.2, ATT, 2.5.18 | Third-party AI disclosure and opt-in (5.1.2(i)), ATT timing, analytics payloads carrying health or location data, ad rules |
| Accounts and login | 5.1.1(v), 4.8, 2.5.13 | Account deletion that really deletes (including user content), Sign in with Apple token revocation, the `private.icloud.com` relay domain, current 4.8 equivalence rules |
| UGC safety | 1.1, 1.2, 1.2.1, 1.5 | Filter, report, block, and contact on every surface, server-enforced; anonymous chat; nonconsensual imagery; creator age controls |
| Age and kids | 2.3.6, 2.3.8, 1.3, 5.1.4 | Age rating answers derived from code; Kids Category; Declared Age Range API usage |
| Health and fitness | 5.1.3, 1.4.1, 2.5.1, 5.2.5 | HealthKit data flows, idempotent HealthKit writes, unused entitlements, medical accuracy claims, regulated medical device declaration |
| Apple services and engagement | 4.5, 5.6.1, 5.3, 5.2.5 | Push marketing consent, review-prompt gating, Apple Music and MusicKit rules, contests with prizes |
| Completeness and software | 2.1, 2.4, 2.5, 1.6 | Xcode and SDK upload minimums mapped to Expo SDKs and EAS images, hidden features and OTA scope (2.5.19), shipped secrets, iPad compatibility |
| Design | 4.1, 4.2, 4.3, 4.7 | Thin WebView wrappers, template and white-label apps, other developers' brands, mini apps and WebView bridges |

Works with Expo (managed and prebuilt), bare React Native, and native Swift or Objective-C Xcode projects, including monorepos with the backend alongside the app.

## The scanner

`scripts/scan.py` is a read-only, standard-library Python pre-scan. The audit runs it first, and you can run it on its own or in CI:

```bash
python3 scripts/scan.py /path/to/app --format md
python3 scripts/scan.py /path/to/app --introspect --ipa build/App.ipa --format json --out scan.json
```

| Flag | Effect |
|---|---|
| `--introspect` | Evaluates the Expo config with `npx --no-install expo config --type introspect` (runs your config code, writes nothing) |
| `--ipa PATH` | Reads a built `.ipa`, `.xcarchive`, or `.app` |
| `--format json\|md` | Machine-readable or human summary |
| `--fail-on blocker` | Exits 1 when blocking signals exist |
| `--today YYYY-MM-DD` | Evaluates dated requirements as of a fixed date |

It reports project layout, native config, purpose strings (flagging generic and development-tool wording), privacy-manifest gaps, the Xcode version your build resolves to against Apple's upload minimums, unused background modes, masked secrets, upcoming Apple deadlines, and grouped code leads tagged with the checks they feed. Its output is a lead sheet, not a verdict.

### In CI

```yaml
name: App Store pre-scan
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: git clone --depth 1 https://github.com/kbcrtz/better-app-store-review "$RUNNER_TEMP/basr"
      - run: python3 "$RUNNER_TEMP/basr/scripts/scan.py" . --format md --fail-on blocker
```

## Example output

```text
VERDICT: NO-GO (2 blockers)

BLOCKER
[5.1.2(i)] Fridge photos sent to a third-party AI without explicit permission  (review)
src/screens/ScanFridge.tsx:112, server/src/ai/identifyIngredients.ts:58
Evidence: the scan button uploads the photo; identifyIngredients posts the image URL
to the AI provider's API. No disclosure or opt-in precedes the first scan.
Fix: one-time disclosure naming the provider and the data, explicit opt-in,
settings toggle, privacy policy and App Privacy labels updated.
Verification: CONFIRMED

Dropped: [3.1.1] Web checkout link on Upgrade screen (refuted: link renders only
when the StoreKit storefront is USA, permitted by 3.1.1(a))
```

The full report format, including the App Review notes draft, is in [`references/report.md`](references/report.md).

## Structure

```
better-app-store-review/
├── SKILL.md                         Orchestration: modes, phases, domain map, rules
├── references/
│   ├── checks.md                    80 checks, false-positive guards, guideline numbering
│   ├── detection.md                 Read-only recipes (ripgrep, Expo introspection, IPA, Swift)
│   ├── agents.md                    Auditor, verifier, and gatekeeper prompt templates
│   ├── report.md                    Report format and a filled-in example
│   ├── rejection.md                 Rejection recovery playbook
│   ├── apple-changes.md             Dated Apple change log and refresh procedure
│   └── facts.json                   Baseline, upload minimums, Expo image map, deadlines
├── scripts/
│   └── scan.py                      Read-only scanner (JSON or Markdown, CI exit codes)
├── skills/better-app-store-review/  Plugin entry point for Claude Code and Codex
├── .claude-plugin/                  Claude Code plugin and marketplace manifests
├── .codex-plugin/                   Codex plugin manifest
├── .agents/plugins/                 Codex marketplace manifest
├── agents/openai.yaml               Codex display metadata
├── CHANGELOG.md
└── LICENSE
```

## Keeping it current

Apple changed the guidelines four times between November 2025 and October 2026. [`references/apple-changes.md`](references/apple-changes.md) records every change that affects a check, and [`references/facts.json`](references/facts.json) holds every value that drifts: the baseline date, upload minimums, the Expo image map, and deadlines. Release notes are in [CHANGELOG.md](CHANGELOG.md).

## Requirements and tradeoffs

- **Subagents for the full audit.** Full and Focused modes spawn subagents. Without them the skill runs each phase in a single context, which is slower and less independent. Quick mode never needs them.
- **Full audits use more tokens.** A full run uses up to 10 auditors plus verifiers. Use Quick mode for a fast pass and the full audit before a submission.
- **Tools:** `python3` for the scanner and `ripgrep` for the recipes. `plutil` and `codesign` (macOS) are only used for optional binary inspection.
- **Static evidence only.** It can't prove runtime behavior, and it can't see App Store Connect settings, so those become checklist items.

## Feedback

False positive, missed rejection, outdated rule, or a rejection the skill should have caught? [Open an issue](https://github.com/kbcrtz/better-app-store-review/issues) with the guideline, what happened, and (if you have it) Apple's exact wording. Leave out your code, credentials, and private app details.

## Disclaimer

This skill checks your code against Apple's public guidance. It can't guarantee approval and doesn't contact Apple. It is not affiliated with or endorsed by Apple Inc.

## License

[MIT](LICENSE)
