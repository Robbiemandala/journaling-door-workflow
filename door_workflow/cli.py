from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (add_hypothesis, build_patterns, capture, decide, duplicate_review, ensure, export_public,
                   plan_workflow, privacy_check, record_deliverable, record_run, replan_workflow, resolve_duplicate, search, verify_workflow, workflow_status)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="door-workflow", description="Local-first capture, provenance, decisions, and honest workflows.")
    p.add_argument("--root", default=".", help="Repository root (default: current directory)")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.set_defaults(fn=lambda a, r: (ensure(r), {"root": str(r), "initialized": True})[1])
    cap = sub.add_parser("capture"); cap.add_argument("--text"); cap.add_argument("--title"); cap.add_argument("--tag", action="append", default=[]); cap.set_defaults(fn=cmd_capture)
    hyp = sub.add_parser("hypothesis"); hyp.add_argument("text"); hyp.add_argument("--source-id", required=True); hyp.add_argument("--confidence", default="unrated"); hyp.set_defaults(fn=lambda a, r: add_hypothesis(r, a.text, source_id=a.source_id, confidence=a.confidence))
    sub.add_parser("duplicates").set_defaults(fn=lambda a, r: duplicate_review(r))
    rd = sub.add_parser("resolve-duplicate"); rd.add_argument("occurrence_id"); rd.add_argument("canonical_id"); rd.add_argument("--note", default=""); rd.set_defaults(fn=lambda a, r: resolve_duplicate(r, a.occurrence_id, a.canonical_id, note=a.note))
    sub.add_parser("patterns").set_defaults(fn=lambda a, r: build_patterns(r))
    find = sub.add_parser("search"); find.add_argument("query", nargs="+"); find.set_defaults(fn=lambda a, r: search(r, " ".join(a.query)))
    dec = sub.add_parser("decide"); dec.add_argument("idea_id"); dec.add_argument("decision", choices=["pursue", "incubate", "clarify", "decline"]); dec.add_argument("--target", default=""); dec.add_argument("--completion-proof", default=""); dec.add_argument("--note", default=""); dec.add_argument("--supersede", action="store_true", help="Explicitly supersede an active pursue decision for this idea"); dec.set_defaults(fn=cmd_decide)
    plan = sub.add_parser("plan-workflow"); plan.add_argument("decision_id"); plan.add_argument("--worker-model", default="unspecified"); plan.set_defaults(fn=lambda a, r: plan_workflow(r, a.decision_id, worker_model=a.worker_model))
    run = sub.add_parser("record-run"); run.add_argument("workflow_id"); run.add_argument("role", choices=["scout", "worker", "verifier"]); run.add_argument("status", choices=["completed", "blocked", "failed"]); run.add_argument("--summary", default=""); run.add_argument("--artifact", action="append", default=[]); run.set_defaults(fn=cmd_run)
    ver = sub.add_parser("verify-workflow"); ver.add_argument("workflow_id"); ver.set_defaults(fn=lambda a, r: verify_workflow(r, a.workflow_id))
    ws = sub.add_parser("workflow-status"); ws.add_argument("workflow_id"); ws.set_defaults(fn=lambda a, r: workflow_status(r, a.workflow_id))
    repl = sub.add_parser("replan-workflow"); repl.add_argument("workflow_id"); repl.add_argument("--reason", required=True); repl.set_defaults(fn=lambda a, r: replan_workflow(r, a.workflow_id, reason=a.reason))
    dl = sub.add_parser("deliver"); dl.add_argument("decision_id"); dl.add_argument("title"); dl.add_argument("--artifact", required=True); dl.add_argument("--proof", required=True); dl.add_argument("--verifier-result", required=True, help="Explicit result from an external semantic verifier"); dl.set_defaults(fn=cmd_deliver)
    sub.add_parser("privacy-check").set_defaults(fn=lambda a, r: privacy_check(r))
    ex = sub.add_parser("export"); ex.add_argument("--out", default="data/exports/public"); ex.add_argument("--include-metadata", action="store_true", help="Opt in to non-anonymized metadata after review"); ex.set_defaults(fn=lambda a, r: export_public(r, r / a.out, include_metadata=a.include_metadata))
    return p


def cmd_capture(a, root):
    text = a.text if a.text is not None else sys.stdin.read()
    return capture(root, text, title=a.title, tags=a.tag)


def cmd_decide(a, root):
    return decide(root, a.idea_id, a.decision, target=a.target, completion_proof=a.completion_proof, note=a.note, supersede=a.supersede)


def cmd_run(a, root):
    return record_run(root, a.workflow_id, a.role, a.status, summary=a.summary, artifacts=a.artifact)


def cmd_deliver(a, root):
    return record_deliverable(root, a.decision_id, a.title, artifact=a.artifact, proof=a.proof, verifier_result=a.verifier_result)


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        result = args.fn(args, root)
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True, default=str))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
