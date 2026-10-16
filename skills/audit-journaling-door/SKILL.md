---
name: audit-journaling-door
description: Audit provenance, human decision gates, workflow receipts, duplicate handling, privacy, and delivery evidence without activating work.
---

# Audit Journaling Door

Use this skill for review or before sharing a repository. Auditing is read-only unless the user explicitly asks for a correction.

## Runtime

Run the commands below from the toolkit checkout, or use an installed `door-workflow` executable with `--root /path/to/target-project`. If the CLI is unavailable, report the missing capability and keep the audit as an unexecuted checklist; do not invent results.

## Checks

- Every writing points to a human source ID.
- Hypotheses carry `origin: agent`, a source ID, and a separate record path.
- Duplicate candidates stay reviewable; recurrence records do not inflate independent-source patterns.
- Pursue decisions contain a concrete target and completion proof and stay within the three-item active limit.
- Workflow roles obey scout → worker → verifier dependencies.
- Completed receipts list existing local artifacts and their hashes.
- A changed artifact makes verification wait; stale evidence is never treated as completion.
- A verifier receipt exists and uses evidence distinct from the worker's artifact.
- `privacy-check` passes before `export` is shared.

Describe missing evidence as `waiting`, `blocked`, or `needs-replan`. Do not repair gaps by writing a plausible claim.
