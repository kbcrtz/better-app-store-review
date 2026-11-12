---
name: better-app-store-review
description: Multi-agent App Store rejection audit for iOS apps built with React Native, Expo, Swift, or Objective-C, checked against Apple's current App Review Guidelines and App Store Connect upload requirements. Runs a read-only scanner, fans out one auditor per guideline domain, has a skeptic try to disprove every serious finding, and reports a verdict with an App Store Connect checklist, age-rating answers derived from code, and a ready-to-paste App Review notes draft. Also offers a quick blocker-only pass, a focused single-area audit, and rejection recovery that diagnoses an App Review rejection and drafts the reply or appeal. On approval it fixes issues and re-audits until an independent gatekeeper says GO. Use for "app store readiness", "will my app get rejected", "pre-submission review", "app review compliance", "quick App Store check", "audit my paywall", "my app was rejected", or "reply to App Review".
metadata:
  author: kbcrtz
  version: "3.0.0"
---

# Better App Store Review (plugin entry point)

This plugin keeps a single copy of the skill at the repository root. Before doing anything
else, read [`../../SKILL.md`](../../SKILL.md) and follow it exactly. Resolve every
`references/` and `scripts/` path relative to that file's directory (the repository root),
not this one.
