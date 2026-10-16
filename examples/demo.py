from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from door_workflow.core import (capture, decide, plan_workflow, record_deliverable, record_run,
                                verify_workflow, write_json)


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    source = capture(root, "A quiet review ritual.\nIdea: Make every claim traceable to a source.", title="Quiet review ritual")
    idea = next((root / "data" / "ideas").glob("*.json"))
    import json
    idea_record = json.loads(idea.read_text())
    decision = decide(root, idea_record["id"], "pursue", target="traceable-review", completion_proof="verification receipt is green")
    workflow = plan_workflow(root, decision["id"], worker_model="demo-worker")
    for name, text in (("scout.md", "Source and constraints inspected."), ("worker.md", "Bounded artifact produced."), ("verify.md", "Independent checks passed.")):
        write_json(root / "artifacts" / (name + ".json"), {"name": name, "text": text})
    record_run(root, workflow["id"], "scout", "completed", artifacts=["artifacts/scout.md.json"])
    record_run(root, workflow["id"], "worker", "completed", artifacts=["artifacts/worker.md.json"])
    record_run(root, workflow["id"], "verifier", "completed", artifacts=["artifacts/verify.md.json"])
    print(verify_workflow(root, workflow["id"]))
    print(record_deliverable(root, decision["id"], "Traceable review ritual", artifact="artifacts/worker.md.json", proof="verifier receipt passed", verifier_result="PASS: completion criterion addressed"))
