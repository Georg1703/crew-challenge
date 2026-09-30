# 0009. AWS resources created by hand, documented in git

**Status:** Accepted
**Date:** 2026-09-30

## Context

The AWS setup is small and created once. An infrastructure-as-code tool would add a state backend
and tooling to learn for little benefit at this size.

## Decision

The owner creates AWS resources in the console following `docs/runbooks/aws-setup.md`. Every JSON
document pasted into AWS (bucket CORS, lifecycle rules, IAM policies) is stored in `infra/aws/`.
Created resource names and ARNs are recorded in `docs/runbooks/aws-inventory.md`. Agents never
create or change AWS resources.

## Consequences

- Simple to start; nothing to install.
- Recreating the setup is a checklist, not a command. The runbook must be kept accurate.
- Configuration drift is possible; the JSON files in git are the reference.
