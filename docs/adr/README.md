# Architecture decision records

Short records of decisions that shape the codebase. Read the relevant ones before changing
architecture. To change a decision, write a new ADR that supersedes the old one and mark the old
one `Superseded` (see [`docs/recipes/new-adr.md`](../recipes/new-adr.md)).

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-monorepo-agent-oriented.md) | Monorepo organized for coding agents | Accepted |
| [0002](0002-django-service-layer.md) | Django apps with service and selector layers | Accepted |
| [0003](0003-session-auth-same-origin.md) | Session authentication on a single origin | Accepted |
| [0004](0004-openapi-contract.md) | OpenAPI contract with a generated TypeScript client | Accepted |
| [0005](0005-real-s3-dev-bucket.md) | Real S3 bucket for local development | Accepted |
| [0006](0006-single-lightsail-instance.md) | One Lightsail instance with Docker Compose | Accepted |
| [0007](0007-pwa-not-native.md) | PWA instead of native apps | Accepted |
| [0008](0008-mediaconvert-transcoding.md) | AWS Elemental MediaConvert for video processing | Accepted |
| [0009](0009-manual-aws-setup.md) | AWS resources created by hand, documented in git | Accepted |
| [0010](0010-crew-terminology.md) | "Crew" as the name for a group | Accepted |

Template: [template.md](template.md)
