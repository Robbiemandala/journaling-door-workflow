# Journaling Door Workflow Agent Contract

This repository is a portable local-first capture and workflow toolkit. Read this file before work.

## Operating rules

- Preserve original writing before interpretation. Capture through `python3 -m door_workflow --root . capture`.
- Human ideas are explicit `Idea:`/`Insight:` lines. Agent hypotheses are separate and must carry a source ID.
- Do not activate an idea without a human `pursue` decision containing a concrete target and completion proof.
- For workflow requests, use the local scout → worker → verifier plan. Keep requested model, resolved model, and routing proof separate. A plan is not evidence that agents ran.
- Record completed roles only with existing local artifacts. Never invent receipts, sources, model routing, or external actions.
- On blocked or failed work, preserve the receipt and replan with a reason before retrying.
- Run `python3 -m unittest discover -s tests -v` and `python3 -m door_workflow --root . privacy-check` before handoff.

## Skill installation

Install skills only into an explicit project-local destination after review:

```bash
python3 scripts/install-skills.py .agents/skills
python3 scripts/install-skills.py .claude/skills
```

Add `--apply` to copy. The installer refuses to overwrite existing skill files and never mutates a global user directory.
