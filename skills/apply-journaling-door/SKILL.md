---
name: apply-journaling-door
description: Apply source-linked human ideas to local project work through explicit decisions, bounded targets, and verified deliverables.
---

# Apply Journaling Door

Use this skill when a source-linked idea is ready to become a real local artifact.

## Runtime

Run the commands below from the toolkit checkout, or use an installed `door-workflow` executable. Pass `--root /path/to/target-project` when applying the workflow to another project. If the CLI is unavailable, stop at a written plan and report that capability gap; do not claim that records or deliverables were created.

## Operating procedure

1. Find the source and idea first:
   `python3 -m door_workflow --root . search "distinctive phrase"`
2. Keep human ideas and agent hypotheses separate. A hypothesis is evidence to inspect, not approval.
3. Ask the human for the decision when it is missing. Record a pursue decision only with both fields:
   `python3 -m door_workflow --root . decide IDEA_ID pursue --target "repo-or-artifact" --completion-proof "inspectable proof"`
4. Plan the bounded workflow:
   `python3 -m door_workflow --root . plan-workflow DECISION_ID --worker-model "codex-worker"`
5. Implement locally. Save a scout note, worker artifact, and verifier report inside the repository. Record each only after the file exists:
   `python3 -m door_workflow --root . record-run WORKFLOW_ID scout completed --artifact notes/scout.md`
6. Check status and verification:
   `python3 -m door_workflow --root . workflow-status WORKFLOW_ID`
   `python3 -m door_workflow --root . verify-workflow WORKFLOW_ID`
7. Record the deliverable only after integrity verification is green and a separate human or external verifier has supplied a semantic result:
   `python3 -m door_workflow --root . deliver DECISION_ID "Title" --artifact artifacts/result.md --proof "verifier report addresses criterion" --verifier-result "PASS: criterion addressed"`

## Human gate

Never activate a queued idea, invent a target, or mark a deliverable complete on a score or plan. The target and completion proof must be concrete enough for another person to inspect.
