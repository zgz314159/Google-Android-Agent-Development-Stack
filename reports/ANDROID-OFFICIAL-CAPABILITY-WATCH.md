# Android Official Capability Watch

Baseline snapshot. On future updates, re-run the capture commands and diff
against this baseline. No automatic update daemon / monitoring service exists
by design — this is an OBSERVE-only record.

Date: 2026-10-03

## Android CLI
- version: `1.0.16486076`
- path: `~/.local/bin/android`
- SDK: `/home/zhong/Android/Sdk`
- top-level commands:
  `auth, completion, create, describe, device, docs, emulator, help, info, init, install, layout, run, screen, sdk, skills, studio, update`

## android create
- catalog (`android create --list`):
  - `empty-activity (default)` — Compose, activity, agp-9
- flags: `--application-id --force --list --min-sdk --name --namespace --output/-o`,
  positional `<template-name>`

## android skills
- total installed skills: **25**
- catalog:
  `adaptive, agp-9-upgrade, android-cli, android-intent-security,
  android-permissions-security, android-profiler, appfunctions, camerax,
  display-glasses-with-jetpack-compose-glimmer, edge-to-edge,
  engage-sdk-integration, leanback-to-compose-tv-migration,
  media3-cast-integration, migrate-xml-views-to-jetpack-compose,
  ml-kit-genai-prompt-api, navigation-3, navigation-event,
  play-billing-library-version-upgrade, play-policy-insights, r8-analyzer,
  restore-credentials, styles, testing-setup, verified-email, wear-compose-m3`
- `android-cli` skill installed for: claude-code, codex, command-code, continue, github-copilot

## android docs (Knowledge Base)
- `android docs search "Navigation 3"` → returns `kb://` results (KB operational).
- fetch with `android docs fetch kb://...`.

## android studio bridge
- subcommands: `analyze-file, check, find-declaration, find-usages,
  open-file, render-compose-preview, version-lookup`
- runtime status at baseline: `No running Studio instances found` → bridge PENDING
  (requires Android Studio Quail 1 or higher running).

## Template Engine
- OBSERVE ONLY. No stable public Agent template API. Not depended upon.

## Lightbuild
- OBSERVE ONLY / NOT PRODUCTION.

## Re-capture commands
```bash
android --version
android --help
android create --list
android skills list
android studio --help
android studio check
```
