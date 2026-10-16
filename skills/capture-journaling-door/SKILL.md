---
name: capture-journaling-door
description: Capture original writing locally, derive only explicitly marked human ideas, and preserve source provenance and duplicate review.
---

# Capture Journaling Door

Use this skill when a person gives you a journal entry, voice transcription, brainstorm, or reflection and asks you to preserve it.

## Runtime

Run the commands below from the toolkit checkout, or install the package so the `door-workflow` executable is on `PATH`. The `--root` value is the target project being captured; it is not the toolkit location. If neither the checkout nor an installed executable is available, stop and report the missing capability rather than simulating a capture.

## Operating procedure

1. Save the exact text before summarizing it:
   `python3 -m door_workflow --root . capture --title "..." --text "..." --tag journal`
2. Capture output includes a stable `source_id` for this occurrence. Keep it in the task notes and use it for any hypothesis or decision.
3. Only lines beginning with `Idea:` or `Insight:` become human ideas. Do not turn an agent paraphrase into a human-authored idea.
4. Before a second import, run `python3 -m door_workflow --root . duplicates`. Exact and probable matches remain reviewable. Resolve an exact repeat with:
   `python3 -m door_workflow --root . resolve-duplicate OCCURRENCE_ID CANONICAL_ID --note "Repeated session"`
5. Run `python3 -m door_workflow --root . privacy-check` before sharing an export.

## Boundary

Do not edit the original source text to improve its style. Do not put raw journal text in agent receipts. If a transcript contains sensitive material, keep `data/transcripts/` private and use the metadata-only export.
