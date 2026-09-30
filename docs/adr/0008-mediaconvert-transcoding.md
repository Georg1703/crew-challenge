# 0008. AWS Elemental MediaConvert for video processing

**Status:** Accepted
**Date:** 2026-09-30

## Context

Phone videos can be up to 20 GB, often 4K HEVC, and must play smoothly on other phones.
Transcoding on the app server would compete with the web app for a small burstable CPU.

## Decision

Use MediaConvert from day one. A Celery task starts a job that reads the original from S3 and
writes HLS (720p and 360p, H.264/AAC) plus a poster image back to S3. MediaConvert reports job
state to an HTTPS webhook in the app (authenticated with a shared secret). Audio proofs are
normalized to AAC `.m4a`.

## Consequences

- Video bytes never touch the app server; quality and speed do not depend on the instance size.
- Roughly $5/month at family scale; cost grows with minutes of video.
- Needs a MediaConvert IAM role and `iam:PassRole` for the app's IAM user.
