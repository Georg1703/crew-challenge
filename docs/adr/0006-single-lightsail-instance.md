# 0006. One Lightsail instance with Docker Compose

**Status:** Accepted
**Date:** 2026-09-30

## Context

The app serves a handful of people at first. Cost and simplicity matter more than scaling.
Options compared: EC2 (~$22-26/month for instance, disk, and IPv4), Lightsail (~$12/month
bundle), and managed databases (+$15/month).

## Decision

Run everything on one Amazon Lightsail instance (2 GB RAM plan) with Docker Compose: Caddy,
gunicorn, Celery worker and beat, Redis, and Postgres. Postgres runs in a container with a nightly
`pg_dump` to S3 kept 14 days. Images come from GitHub Container Registry; GitHub Actions deploys
over SSH. The server uses a least-privilege IAM user key (Lightsail has no instance roles).

## Consequences

- About $19-20/month total including MediaConvert and S3.
- Worst case data loss is one day of check-ins; acceptable for now. Moving to a managed database
  later is a dump, a restore, and one `DATABASE_URL` change.
- No load balancer or autoscaling. A Lightsail snapshot can be exported to EC2 if needed.
- An access key lives on the server; it is scoped tightly and rotated periodically.
