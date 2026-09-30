# 0003. Session authentication on a single origin

**Status:** Accepted
**Date:** 2026-09-30

## Context

The PWA and the API are ours and can be served from the same domain. Token schemes (JWT) add
refresh logic and storage decisions in the browser.

## Decision

Use Django's session cookie with CSRF protection. The SPA and API share one origin: Vite proxies
`/api` and `/admin` locally, Caddy does it in production. Sessions last one year so people stay
logged in on their phones.

## Consequences

- No token storage in the browser, no refresh flow, no CORS for the API.
- Django admin works with the same login.
- A native app or third-party client later would need a separate auth method.
