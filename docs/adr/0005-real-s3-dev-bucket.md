# 0005. Real S3 bucket for local development

**Status:** Accepted
**Date:** 2026-09-30

## Context

Browser multipart uploads depend on S3 CORS, the `ETag` response header, and presigned URL
behavior. S3 emulators differ in exactly those details.

## Decision

Local development uses a real bucket, `cc-dev-media`, through an AWS CLI profile that can only
reach that bucket (and MediaConvert in dev). Automated tests never touch AWS: they use moto or the
in-memory storage adapter.

## Consequences

- Upload bugs show up locally, not in production.
- Local development needs an AWS profile and internet access for media features.
- Cost is a few cents per month; a lifecycle rule cleans up abandoned uploads.
