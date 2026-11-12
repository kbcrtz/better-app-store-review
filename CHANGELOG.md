# Changelog

All notable changes to this skill. Versions follow semantic versioning; the Apple baseline
for each release is the App Review Guidelines "Last Updated" date it was checked against.

## 3.0.0 - 2026-11-11

Apple baseline: App Review Guidelines last updated October 16, 2026.

### Added
- Read-only scanner (`scripts/scan.py`, Python standard library only) for Expo, bare React
  Native, and native Swift or Objective-C projects, plus built `.ipa`, `.xcarchive`, or
  `.app` files. Outputs JSON or Markdown and can fail a CI job on blocking signals.
- Quick mode (blocker checks only, single agent), Focused mode (one area), and Rejection
  recovery mode (diagnose an App Review message, choose reply, metadata fix, new build,
  bug-fix deferral, or appeal, and draft the text).
- App Review notes draft in every report.
- `references/facts.json`: one home for the baseline date, upload minimums, the Expo EAS
  image to Xcode mapping, Sign in with Apple relay domains, and upcoming deadlines.
- Freshness check against Apple's live guidelines date at the start of every run, and a
  dated change log of Apple policy changes since 2024 (`references/apple-changes.md`).
- Claude Code plugin and marketplace manifests, Codex plugin and marketplace manifests.
- New domains and checks: data sharing and third-party AI consent (5.1.2(i)), age rating
  answers derived from code and age-assurance laws, Apple services and engagement (push,
  review prompts, Apple Music, contests), upload toolchain minimums, hidden features and
  OTA scope (2.5.19), Sign in with Apple token revocation and relay domain change, session
  replay consent (2.5.14), device compatibility, and more (10 domains, 80 checks).
- Native Swift and Objective-C detection patterns.

### Changed
- 4.8 check rewritten for the current "equivalent login service" rule.
- Account deletion check follows Apple's guidance: a direct link to the exact deletion page
  is allowed; deactivate-only, support-only, and deletion that keeps user content are not.
- Guideline numbers corrected: hidden features 2.5.19, IPv6 2.5.5, purpose strings
  5.1.1(ii).
- Purchase link-outs are judged by StoreKit storefront gating (US storefront exemption and
  regional entitlements).
- Native configuration comes from Expo introspection or a built binary; a gitignored
  `ios/` directory in a CNG project is never used as evidence.
- Findings carry a category (review, upload, removal, security, legal, hygiene); only
  review, upload, removal, and security findings affect the verdict.
- Every ripgrep recipe passes an explicit path.

## 2.0.0 - 2026-07

Apple baseline: App Review Guidelines as of July 2026.

- Multi-agent audit: parallel domain auditors, skeptic verification of every BLOCKER and
  HIGH finding, approval-gated fix loop, and a blind gatekeeper verdict.
- Seven domains: payments, privacy, accounts, UGC, health, completeness, design.
