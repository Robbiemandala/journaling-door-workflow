---
name: dynamic-workflow
description: Plan and operate a small scout-worker-verifier team with honest routing, evidence-backed receipts, retry, and replan behavior.
---

# Dynamic Workflow

Use this skill when the user says “workflow,” “run a workflow,” or asks for delegated parallel work. The portable runtime records a team plan; it does not pretend to launch Codex or Claude.

## Runtime and delegation

Run the CLI from the toolkit checkout or use an installed `door-workflow` executable; use `--root /path/to/target-project` for the project under work. If native delegation tools are available, actually spawn the bounded roles and then invoke the documented CLI commands to record their returned local evidence. If native tools are unavailable, stop at `plan-workflow` and state the missing capability. Never simulate a team by writing completed receipts without real role outputs.

## Team shape

Use the least-capable sufficient role set:

1. **Scout** reads the source, constraints, and acceptance criteria and writes a bounded findings note.
2. **Worker** makes the smallest coherent implementation and writes the artifact.
3. **Verifier** independently checks the artifact, receipt hashes, and completion proof.

The scout is read-only and handles untrusted source material. Give each worker an explicit ownership boundary; independent workers are appropriate only for disjoint files or questions. The verifier must not verify its own implementation. Keep external actions empty unless separately authorized.

Adapt the topology to the task: use parallel scouts when uncertainty is broad, one worker for a narrow change, and independent workers only where ownership is disjoint. Retry a failed worker once with precise verifier feedback. If it fails again, change the approach or document an escalation reason before using a more capable role.

Create the plan with `plan-workflow`. Keep `requested_worker_model`, `resolved_worker_model`, and `routing_proven` distinct. If the native runtime does not expose resolution, preserve `resolved_worker_model: unknown` and `routing_proven: false`.

## Receipts and retry

Record a completed role only after its local evidence file exists. The CLI enforces dependency order and stores a SHA-256 hash. A verifier must use a distinct report artifact; changing any evidence causes `verify-workflow` to return `waiting`.

When a role is blocked or fails, record that status, explain the missing input, and run:
`python3 -m door_workflow --root . replan-workflow WORKFLOW_ID --reason "..."`
Then rerun from scout. Do not overwrite the earlier receipt. A plan, a manually entered receipt, and an integrity check do not prove that an agent ran or that the completion criterion is semantically true; delivery needs a separately recorded external verifier result.

## Honest language

The ledger says: “This receipt records a user-submitted role run and its local evidence; actual agent execution is unproven by the ledger alone.” Do not claim a model ran, routing was proven, or an external action occurred unless a real runner supplies independent evidence.
