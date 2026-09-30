# 0007. PWA instead of native apps

**Status:** Accepted
**Date:** 2026-09-30

## Context

The crew uses both iPhones and Android phones. Building and publishing two native apps is
expensive for a small project.

## Decision

Ship a PWA. It installs from the browser (Android prompt, iOS "Add to Home Screen" guide),
supports Web Push on iOS 16.4+ once installed, and records audio and video through the browser.

## Consequences

- One codebase, instant updates, no app store review.
- iOS limits: no background uploads or sync, manual install, storage can be evicted. The upload
  design and server-side scheduling account for this.
- If background uploads become essential, a native wrapper can be added later.
