# Journaling Door Workflow

A small, local-first version of the Journaling Door and dynamic workflow practice for Codex and Claude Code users. It keeps original writing, human ideas, agent hypotheses, decisions, workflow receipts, and deliverables inspectable in one repository.

Prerequisites are Python 3.10 or newer and a local Codex or Claude Code installation if you want an agent to use the skills. The core CLI has no runtime package or API-key dependency. Run commands from this repository, or pass `--root /path/to/your/project`.

This repository is intentionally portable. It uses Python's standard library, JSON records, no hosted service, no API key, no private vault, and no global installation. It captures the design patterns of a larger personal system while leaving out its private records, dashboards, audio importers, Obsidian projections, and model-specific integrations.

## Quick start

```bash
python3 -m door_workflow --root . init
python3 -m door_workflow --root . capture --title "A calmer review loop" --text $'Today I noticed a review loop can stay calm.\nIdea: Keep the source visible while agents work from a bounded brief.' --tag demo
python3 -m door_workflow --root . patterns
python3 -m door_workflow --root . search review
```

Capture writes a source transcript and linked writing record. Only lines beginning with `Idea:` or `Insight:` become human ideas. An agent hypothesis is always a separate record and must name the source it came from:

```bash
python3 -m door_workflow hypothesis "A bounded verifier may reduce review anxiety." --source-id SOURCE_ID
```

The human decision gate requires a concrete target and completion proof before work can be pursued:

```bash
python3 -m door_workflow decide IDEA_ID pursue \
  --target "portable-review-loop" \
  --completion-proof "A verifier receipt and a public artifact exist"
python3 -m door_workflow plan-workflow DECISION_ID --worker-model "codex-worker"
```

The workflow is a plan until receipts exist. A run cannot be recorded as completed without an existing artifact inside this repository; worker and verifier runs cannot skip their dependencies. A verifier checks receipt hashes for staleness. Recording `blocked` or `failed` makes the plan visible as blocked or needing a replan:

```bash
python3 -m door_workflow record-run WORKFLOW_ID scout completed --artifact notes/scout.md
python3 -m door_workflow record-run WORKFLOW_ID worker completed --artifact artifacts/work.md
python3 -m door_workflow record-run WORKFLOW_ID verifier completed --artifact artifacts/verification.md
python3 -m door_workflow verify-workflow WORKFLOW_ID
python3 -m door_workflow deliver DECISION_ID "Portable review loop" --artifact artifacts/work.md --proof "verification receipt is green" --verifier-result "PASS: completion criterion addressed"
```

The CLI does not claim to have invoked Codex, Claude, or any other agent. A real runner may write artifacts and then use `record-run`; the receipt records which role and local evidence were submitted, but actual agent execution remains unproven by the ledger. `verify-workflow` checks receipt and artifact integrity only. Delivery additionally requires a separately supplied external verifier result that addresses the completion criterion. The requested model is recorded separately from the resolved model, and the default is `resolved_worker_model: unknown` with `routing_proven: false`.

## Portable skills

The `skills/` directory contains discoverable `SKILL.md` folders. Review them, then install into the project you want to work on. The installer resolves its source relative to this repository, requires an explicit destination, and refuses to overwrite an existing file:

```bash
python3 scripts/install-skills.py /path/to/project/.agents/skills --apply
python3 scripts/install-skills.py /path/to/project/.claude/skills --apply
```

Without `--apply`, the command is a dry run. It never mutates a global user directory. If a destination already contains one of these skill names, choose a different project-local destination or review the conflict yourself.

- `skills/capture-journaling-door/SKILL.md` preserves original writing and asks for explicit idea markers.
- `skills/apply-journaling-door/SKILL.md` requires source IDs, decisions, targets, and completion proof before implementation.
- `skills/audit-journaling-door/SKILL.md` checks provenance, duplicates, human gates, and receipt-backed delivery.
- `skills/dynamic-workflow/SKILL.md` defines scout → worker → verifier sequencing and honest receipts.

After installation, a natural-language request such as “Capture this reflection, keep my ideas separate from agent hypotheses, and prepare a workflow with an independent verifier” should activate the relevant skill. The concrete local loop remains inspectable through `capture`, `decide`, `plan-workflow`, `record-run`, `verify-workflow`, and `deliver` commands.

## Privacy and export

Run `python3 -m door_workflow privacy-check` before sharing. It rejects absolute user paths and email addresses anywhere in the repository. `python3 -m door_workflow export --out data/exports/public` writes counts and record types only. `--include-metadata` is an explicit opt-in for non-anonymized titles, proofs, and other metadata after review. Keep `data/transcripts/` private when the original writing is sensitive.

## Tests and demo

```bash
python3 examples/demo.py
python3 -m unittest discover -s tests -v
```

The tests use temporary directories and fictional content. They prove the capture → idea → pursue → plan → receipt → integrity verification → externally reported semantic result → deliverable loop, dependency ordering, stale evidence detection, duplicate review, source-root counting, active pursuit limits, malformed-source handling, and privacy/export behavior.

## Source boundary

This is a clean-room portable implementation informed by the public shape of the source repositories' mechanisms. It does not copy private vault files, identity or business data, runtime ledgers, personal paths, transcript examples, git history, or global skill configuration. The source repositories remain read-only.

## License

License selection is pending. This repository is public for inspection and evaluation; no open-source license has been granted yet. See `LICENSE.pending`.
