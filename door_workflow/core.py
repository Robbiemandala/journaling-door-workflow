from __future__ import annotations

import hashlib
import json
import re
import secrets
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


FOLDERS = (
    "transcripts", "writings", "ideas", "hypotheses", "decisions", "workflows",
    "deliverables", "receipts", "derived", "exports",
)
STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "we", "with", "you"}
MAX_ACTIVE_PURSUITS = 3


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def digest(value: str | bytes | dict[str, Any]) -> str:
    if isinstance(value, dict):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def ident(prefix: str, value: str) -> str:
    return f"{prefix}-{digest(value)[:12]}"


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return result[:64] or "record"


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOPWORDS and len(w) > 2]


def ensure(root: Path) -> None:
    for folder in FOLDERS:
        (root / "data" / folder).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def records(root: Path, folder: str) -> list[dict[str, Any]]:
    path = root / "data" / folder
    if not path.exists():
        return []
    result = []
    for item in sorted(path.glob("*.json")):
        try:
            result.append(read_json(item))
        except (OSError, json.JSONDecodeError):
            continue
    return result


def capture(root: Path, text: str, *, title: str | None = None, tags: Iterable[str] = ()) -> dict[str, Any]:
    """Capture original text and derive human ideas only from explicit markers."""
    ensure(root)
    clean = text.strip()
    if not clean:
        raise ValueError("capture text cannot be empty")
    # Each capture is a distinct occurrence. The content hash enables review without
    # silently collapsing a repeated session into the first one.
    source_id = ident("source", clean + secrets.token_hex(8))
    title = title or next((line.strip(" #-") for line in clean.splitlines() if line.strip()), "Untitled reflection")[:100]
    source = {
        "id": source_id, "type": "transcript", "title": title, "created_at": now(),
        "sha256": digest(clean), "tags": sorted(set(tags)), "text": clean,
        "provenance": {"origin": "human", "capture": "direct", "source_root": source_id},
    }
    source_path = root / "data" / "transcripts" / f"{source_id}.json"
    if source_path.exists():
        return read_json(source_path)
    write_json(source_path, source)
    writing = {"id": ident("writing", source_id), "type": "writing", "title": title,
               "created_at": source["created_at"], "source_id": source_id, "text": clean,
               "provenance": {"origin": "human", "source_root": source_id}}
    write_json(root / "data" / "writings" / f"{writing['id']}.json", writing)
    for line in clean.splitlines():
        match = re.match(r"\s*(?:idea|insight)\s*:\s*(.+)", line, flags=re.I)
        if not match:
            continue
        idea_text = match.group(1).strip()
        idea = {"id": ident("idea", source_id + idea_text), "type": "idea", "title": idea_text[:100],
                "text": idea_text, "status": "fresh", "source_id": source_id,
                "provenance": {"origin": "human", "source_root": source_id, "evidence": "explicit Idea/Insight marker"}}
        write_json(root / "data" / "ideas" / f"{idea['id']}.json", idea)
    return source


def add_hypothesis(root: Path, text: str, *, source_id: str, confidence: str = "unrated") -> dict[str, Any]:
    ensure(root)
    if not any(item.get("id") == source_id for item in records(root, "transcripts")):
        raise ValueError(f"unknown source_id: {source_id}")
    item = {"id": ident("hypothesis", source_id + text), "type": "hypothesis", "title": text[:100],
            "text": text, "status": "unreviewed", "confidence": confidence, "source_id": source_id,
            "provenance": {"origin": "agent", "source_root": source_id, "agent_generated": True}}
    write_json(root / "data" / "hypotheses" / f"{item['id']}.json", item)
    return item


def duplicate_review(root: Path) -> list[dict[str, Any]]:
    docs = records(root, "transcripts")
    matches = []
    for index, left in enumerate(docs):
        for right in docs[index + 1:]:
            if left.get("sha256") == right.get("sha256"):
                matches.append({"left": left["id"], "right": right["id"], "kind": "exact", "similarity": 1.0, "status": "review"})
                continue
            a, b = set(tokens(left.get("text", ""))), set(tokens(right.get("text", "")))
            score = len(a & b) / len(a | b) if a | b else 0.0
            if score >= 0.72:
                matches.append({"left": left["id"], "right": right["id"], "kind": "probable", "similarity": round(score, 3), "status": "review"})
    return matches


def resolve_duplicate(root: Path, occurrence_id: str, canonical_id: str, *, note: str = "") -> dict[str, Any]:
    occurrence_path = root / "data" / "transcripts" / f"{occurrence_id}.json"
    canonical_path = root / "data" / "transcripts" / f"{canonical_id}.json"
    if not occurrence_path.exists() or not canonical_path.exists() or occurrence_id == canonical_id:
        raise ValueError("resolve-duplicate requires two distinct existing transcript IDs")
    occurrence = read_json(occurrence_path)
    canonical = read_json(canonical_path)
    if occurrence.get("sha256") != canonical.get("sha256"):
        raise ValueError("only exact duplicate captures can be resolved automatically")
    occurrence["recurrence_of"] = canonical_id
    occurrence["recurrence_note"] = note or "Repeated occurrence retained as recurrence evidence."
    write_json(occurrence_path, occurrence)
    return occurrence


def build_patterns(root: Path) -> dict[str, Any]:
    docs = records(root, "writings")
    recurrences = {str(item.get("id")) for item in records(root, "transcripts") if item.get("recurrence_of")}
    by_token: dict[str, set[str]] = {}
    for doc in docs:
        if doc.get("source_id") in recurrences:
            continue
        source = str(doc.get("source_id") or doc.get("id"))
        for token in set(tokens(doc.get("text", ""))):
            by_token.setdefault(token, set()).add(source)
    patterns = [{"token": token, "independent_sources": len(sources), "source_ids": sorted(sources)}
                for token, sources in by_token.items() if len(sources) >= 2]
    patterns.sort(key=lambda row: (-row["independent_sources"], row["token"]))
    output = {"generated_at": now(), "patterns": patterns}
    write_json(root / "data" / "derived" / "patterns.json", output)
    return output


def search(root: Path, query: str) -> list[dict[str, Any]]:
    terms = tokens(query)
    result = []
    for folder in ("writings", "ideas", "hypotheses", "decisions", "deliverables"):
        for item in records(root, folder):
            hay = " ".join(str(item.get(k, "")) for k in ("title", "text", "summary", "target"))
            score = sum(hay.lower().count(term) for term in terms)
            if score:
                result.append({"folder": folder, "id": item.get("id"), "title": item.get("title"), "score": score, "source_id": item.get("source_id")})
    return sorted(result, key=lambda row: (-row["score"], str(row["title"])))


def decide(root: Path, idea_id: str, decision: str, *, target: str = "", completion_proof: str = "", note: str = "", supersede: bool = False) -> dict[str, Any]:
    if decision not in {"pursue", "incubate", "clarify", "decline"}:
        raise ValueError("decision must be pursue, incubate, clarify, or decline")
    idea = next((item for item in records(root, "ideas") + records(root, "hypotheses") if item.get("id") == idea_id), None)
    if not idea:
        raise ValueError(f"unknown idea: {idea_id}")
    if decision == "pursue" and (not target.strip() or not completion_proof.strip()):
        raise ValueError("pursue requires an explicit target and completion_proof")
    existing_active = [item for item in records(root, "decisions") if item.get("decision") == "pursue" and item.get("status") == "active" and item.get("idea_id") == idea_id]
    if existing_active and decision == "pursue" and not supersede:
        raise ValueError("this idea already has an active pursue decision; use supersede=True with an explicit replacement note")
    if decision == "pursue":
        active = [item for item in records(root, "decisions") if item.get("decision") == "pursue" and item.get("status") == "active" and item.get("idea_id") != idea_id]
        if len(active) >= MAX_ACTIVE_PURSUITS:
            raise ValueError(f"active pursue limit reached ({MAX_ACTIVE_PURSUITS}); complete or pause a decision first")
    item = {"id": ident("decision", idea_id + decision + note), "type": "decision", "idea_id": idea_id,
            "decision": decision, "target": target, "completion_proof": completion_proof, "note": note,
            "created_at": now(), "status": "active" if decision == "pursue" else "recorded",
            "source_id": idea.get("source_id"), "provenance": {"origin": "human", "source_root": idea.get("source_id")}}
    write_json(root / "data" / "decisions" / f"{item['id']}.json", item)
    for previous in existing_active:
        previous["status"] = "superseded"
        previous["superseded_by"] = item["id"]
        write_json(root / "data" / "decisions" / f"{previous['id']}.json", previous)
    idea["decision_id"] = item["id"]
    idea["decision"] = decision
    folder = "ideas" if idea.get("type") == "idea" else "hypotheses"
    write_json(root / "data" / folder / f"{idea_id}.json", idea)
    return item


def plan_workflow(root: Path, decision_id: str, *, worker_model: str = "unspecified") -> dict[str, Any]:
    decision = next((item for item in records(root, "decisions") if item.get("id") == decision_id), None)
    if not decision or decision.get("decision") != "pursue" or decision.get("status") != "active":
        raise ValueError("workflow requires the current active pursued decision")
    steps = [
        {"id": "scout", "role": "scout", "purpose": "inspect source and constraints", "depends_on": [], "status": "planned", "receipt_id": None},
        {"id": "worker", "role": "worker", "purpose": "produce a bounded implementation or artifact", "depends_on": ["scout"], "status": "planned", "receipt_id": None},
        {"id": "verifier", "role": "verifier", "purpose": "independently test claims and completion proof", "depends_on": ["worker"], "status": "planned", "receipt_id": None},
    ]
    item = {"id": ident("workflow", decision_id + worker_model), "type": "workflow_plan", "decision_id": decision_id,
            "created_at": now(), "status": "planned", "revision": 1, "requested_worker_model": worker_model,
            "resolved_worker_model": "unknown", "routing_proven": False, "steps": steps,
            "honesty": "Planning a team does not claim that any agent ran."}
    write_json(root / "data" / "workflows" / f"{item['id']}.json", item)
    return item


def _artifact_path(root: Path, artifact: str, *, require_canonical: bool = False) -> tuple[Path, str]:
    """Return an existing, non-symlink artifact and its canonical repo-relative path."""
    if not isinstance(artifact, str) or not artifact.strip():
        raise ValueError("artifact path must be a non-empty string")
    supplied = Path(artifact)
    if supplied.is_absolute():
        raise ValueError("artifact path must be relative to the repository root")
    root_path = root.resolve()
    lexical_path = root / supplied
    # Checking every lexical component prevents an in-root symlink from being used
    # as an alternate name for an artifact.
    current = root
    for component in supplied.parts:
        if component == ".":
            continue
        if component == "..":
            current = current.parent
        else:
            current = current / component
        if current.is_symlink():
            raise ValueError("artifact path cannot contain a symlink")
    path = lexical_path.resolve()
    if path == root_path or root_path not in path.parents:
        raise ValueError("artifact must be inside repository root")
    if not path.is_file():
        raise ValueError("artifact must be an existing regular file")
    canonical = path.relative_to(root_path).as_posix()
    if require_canonical and artifact != canonical:
        raise ValueError("artifact evidence path is not canonical repository-relative")
    return path, canonical


def record_run(root: Path, workflow_id: str, role: str, status: str, *, summary: str = "", artifacts: Iterable[str] = ()) -> dict[str, Any]:
    if role not in {"scout", "worker", "verifier"} or status not in {"completed", "blocked", "failed"}:
        raise ValueError("role must be scout/worker/verifier and status completed/blocked/failed")
    workflow = next((item for item in records(root, "workflows") if item.get("id") == workflow_id), None)
    if not workflow:
        raise ValueError(f"unknown workflow: {workflow_id}")
    if workflow.get("status") in {"blocked", "needs-replan"}:
        raise ValueError("workflow is blocked; replan-workflow with a reason before retrying")
    step = next(item for item in workflow["steps"] if item["role"] == role)
    previous_runs = [item for item in records(root, "receipts") if item.get("workflow_id") == workflow_id and item.get("workflow_revision", 1) == workflow.get("revision", 1) and item.get("status") == "completed"]
    completed_roles = {item.get("role") for item in previous_runs}
    missing_dependencies = [dependency for dependency in step.get("depends_on", []) if dependency not in completed_roles]
    if missing_dependencies:
        raise ValueError(f"cannot run {role} before completed dependencies: {', '.join(missing_dependencies)}")
    artifact_paths = []
    evidence = []
    for artifact in artifacts:
        path, canonical = _artifact_path(root, artifact)
        if canonical in artifact_paths:
            raise ValueError("completed run artifacts must not contain aliases for the same file")
        artifact_paths.append(canonical)
        evidence.append({"path": canonical, "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size})
    if status == "completed" and not evidence:
        raise ValueError("completed run requires at least one existing artifact for evidence")
    run = {"id": ident("run", workflow_id + role + secrets.token_hex(8)), "type": "workflow_run",
           "workflow_id": workflow_id, "workflow_revision": workflow.get("revision", 1), "role": role, "status": status, "summary": summary,
           "artifacts": artifact_paths, "artifact_evidence": evidence, "started_at": now(), "finished_at": now(),
           "external_actions": [], "honest_claim": f"This receipt records a user-submitted {role} run and its local evidence; actual agent execution is unproven by the ledger alone."}
    write_json(root / "data" / "receipts" / f"{run['id']}.json", run)
    step["status"] = status
    step["receipt_id"] = run["id"]
    if status == "blocked":
        workflow["status"] = "blocked"
    elif status == "failed":
        workflow["status"] = "needs-replan"
    elif all(item.get("status") == "completed" for item in workflow["steps"]):
        workflow["status"] = "awaiting-verification"
    write_json(root / "data" / "workflows" / f"{workflow_id}.json", workflow)
    return run


def _valid_revision(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _validate_completed_receipt(root: Path, run: Any, workflow_id: str, revision: int) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate receipt structure before trusting it as integrity evidence."""
    if not isinstance(run, dict):
        return None, ["invalid receipt schema: top-level record must be an object"]
    if run.get("workflow_id") != workflow_id:
        return None, []
    if run.get("status") != "completed":
        return None, []
    errors = []
    if not isinstance(run.get("role"), str) or run["role"] not in {"scout", "worker", "verifier"}:
        errors.append("invalid receipt schema: role must be scout, worker, or verifier")
    if not _valid_revision(run.get("workflow_revision")):
        errors.append("invalid receipt schema: workflow_revision must be a positive integer")
    elif run["workflow_revision"] != revision:
        return None, []
    artifacts = run.get("artifacts")
    evidence = run.get("artifact_evidence")
    if not isinstance(artifacts, list) or not all(isinstance(path, str) for path in artifacts):
        errors.append("invalid receipt schema: artifacts must be a list of paths")
        artifacts = []
    if not isinstance(evidence, list) or not evidence:
        errors.append("invalid receipt schema: artifact_evidence must be a non-empty list")
        evidence = []
    normalized_artifacts = []
    for artifact in artifacts:
        try:
            _, canonical = _artifact_path(root, artifact, require_canonical=True)
            normalized_artifacts.append(canonical)
        except ValueError as error:
            errors.append(f"invalid receipt artifact: {error}")
    if len(normalized_artifacts) != len(set(normalized_artifacts)):
        errors.append("invalid receipt schema: artifacts contain duplicate paths")
    normalized_evidence = []
    for entry in evidence:
        if not isinstance(entry, dict):
            errors.append("invalid receipt schema: artifact_evidence entries must be objects")
            continue
        path, checksum, size = entry.get("path"), entry.get("sha256"), entry.get("bytes")
        if not isinstance(path, str):
            errors.append("invalid receipt schema: evidence path must be a string")
            continue
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            errors.append("invalid receipt schema: evidence sha256 must be a lowercase SHA-256 hex digest")
            continue
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append("invalid receipt schema: evidence bytes must be a non-negative integer")
            continue
        try:
            artifact_path, canonical = _artifact_path(root, path, require_canonical=True)
        except ValueError as error:
            errors.append(f"invalid receipt evidence path: {error}")
            continue
        normalized_evidence.append({"path": canonical, "sha256": checksum, "bytes": size,
                                    "actual_sha256": digest(artifact_path.read_bytes()),
                                    "actual_bytes": artifact_path.stat().st_size})
    evidence_paths = [entry["path"] for entry in normalized_evidence]
    if len(evidence_paths) != len(set(evidence_paths)):
        errors.append("invalid receipt schema: artifact_evidence contains duplicate paths")
    if normalized_artifacts != evidence_paths:
        errors.append("invalid receipt schema: artifacts and artifact_evidence paths must match in order")
    if errors:
        return None, errors
    return {**run, "artifacts": normalized_artifacts, "artifact_evidence": normalized_evidence}, []


def verify_workflow(root: Path, workflow_id: str) -> dict[str, Any]:
    workflow = next((item for item in records(root, "workflows") if isinstance(item, dict) and item.get("id") == workflow_id), None)
    if not workflow:
        raise ValueError(f"unknown workflow: {workflow_id}")
    waiting_reasons: list[str] = []
    revision = workflow.get("revision")
    steps = workflow.get("steps")
    if not _valid_revision(revision):
        waiting_reasons.append("invalid workflow schema: revision must be a positive integer")
        revision = 1
    if not isinstance(steps, list) or not all(isinstance(step, dict) and step.get("role") in {"scout", "worker", "verifier"} for step in steps):
        waiting_reasons.append("invalid workflow schema: steps must contain valid role objects")
        steps = []
    expected_roles = [step["role"] for step in steps]
    if len(expected_roles) != len(set(expected_roles)) or set(expected_roles) != {"scout", "worker", "verifier"}:
        waiting_reasons.append("invalid workflow schema: steps must contain scout, worker, and verifier exactly once")
    by_role: dict[str, dict[str, Any]] = {}
    for run in records(root, "receipts"):
        valid_run, errors = _validate_completed_receipt(root, run, workflow_id, revision)
        waiting_reasons.extend(errors)
        if valid_run:
            by_role[valid_run["role"]] = valid_run
    missing = [role for role in expected_roles if role not in by_role]
    worker_artifacts = {entry["path"] for entry in by_role.get("worker", {}).get("artifact_evidence", [])}
    verifier_artifacts = {entry["path"] for entry in by_role.get("verifier", {}).get("artifact_evidence", [])}
    independent = "verifier" in by_role and by_role["verifier"].get("role") == "verifier" and not worker_artifacts.intersection(verifier_artifacts)
    stale = []
    for run in by_role.values():
        for evidence in run["artifact_evidence"]:
            if evidence["actual_sha256"] != evidence["sha256"] or evidence["actual_bytes"] != evidence["bytes"]:
                stale.append(evidence["path"])
    if "verifier" in by_role and worker_artifacts.intersection(verifier_artifacts):
        waiting_reasons.append("verifier evidence overlaps worker evidence")
    complete = not missing and independent and not stale and not waiting_reasons
    result = {"workflow_id": workflow_id, "verified_at": now(), "status": "integrity_verified" if complete else "waiting",
              "integrity_verified": complete, "semantic_status": "unverified",
              "completed_roles": sorted(by_role), "missing_roles": missing, "independent_verifier_receipt": independent,
              "stale_artifacts": stale, "waiting_reasons": sorted(set(waiting_reasons)),
              "routing_proven": bool(workflow.get("routing_proven")), "claims": {"agents_actually_ran": False,
              "workflow_integrity": complete, "semantic_completion": False}}
    write_json(root / "data" / "derived" / f"verification-{workflow_id}.json", result)
    if result["status"] == "integrity_verified":
        workflow["status"] = "integrity_verified"
        write_json(root / "data" / "workflows" / f"{workflow_id}.json", workflow)
    return result


def workflow_status(root: Path, workflow_id: str) -> dict[str, Any]:
    workflow = next((item for item in records(root, "workflows") if item.get("id") == workflow_id), None)
    if not workflow:
        raise ValueError(f"unknown workflow: {workflow_id}")
    return {"workflow_id": workflow_id, "revision": workflow.get("revision", 1), "status": workflow.get("status"),
            "steps": [{"role": step["role"], "status": step.get("status"), "depends_on": step.get("depends_on", [])} for step in workflow.get("steps", [])],
            "requested_worker_model": workflow.get("requested_worker_model"), "resolved_worker_model": workflow.get("resolved_worker_model"),
            "routing_proven": workflow.get("routing_proven", False)}


def replan_workflow(root: Path, workflow_id: str, *, reason: str) -> dict[str, Any]:
    workflow = next((item for item in records(root, "workflows") if item.get("id") == workflow_id), None)
    if not workflow:
        raise ValueError(f"unknown workflow: {workflow_id}")
    workflow["revision"] = int(workflow.get("revision", 1)) + 1
    workflow["status"] = "planned"
    workflow["replan_reason"] = reason
    for step in workflow["steps"]:
        step["status"] = "planned"
        step["receipt_id"] = None
    write_json(root / "data" / "workflows" / f"{workflow_id}.json", workflow)
    return workflow


def record_deliverable(root: Path, decision_id: str, title: str, *, artifact: str, proof: str, verifier_result: str) -> dict[str, Any]:
    decision = next((item for item in records(root, "decisions") if item.get("id") == decision_id), None)
    if not decision or decision.get("decision") != "pursue":
        raise ValueError("deliverable requires a pursued decision")
    if not artifact.strip() or not proof.strip() or not verifier_result.strip():
        raise ValueError("deliverable requires artifact, completion proof, and an explicit verifier result")
    workflow = next((item for item in records(root, "workflows") if item.get("decision_id") == decision_id), None)
    if not workflow or workflow.get("status") != "integrity_verified":
        raise ValueError("deliverable requires an integrity-verified workflow receipt")
    artifact_input = Path(artifact)
    if artifact_input.is_absolute():
        raise ValueError("deliverable artifact must be a relative path inside the repository")
    artifact_path = (root / artifact_input).resolve()
    if root.resolve() not in artifact_path.parents or artifact_path == root.resolve() or (root / artifact_input).is_symlink() or not artifact_path.is_file():
        raise ValueError("deliverable artifact must be an existing regular file inside the repository and cannot be a symlink")
    worker_runs = [item for item in records(root, "receipts") if item.get("workflow_id") == workflow["id"] and item.get("workflow_revision", 1) == workflow.get("revision", 1) and item.get("role") == "worker" and item.get("status") == "completed"]
    worker_evidence = {entry.get("path"): entry for run in worker_runs for entry in run.get("artifact_evidence", [])}
    relative_artifact = str(artifact_path.relative_to(root.resolve()))
    evidence = worker_evidence.get(relative_artifact)
    actual_hash = digest(artifact_path.read_bytes())
    if not evidence or evidence.get("sha256") != actual_hash:
        raise ValueError("deliverable artifact must match a verified worker receipt hash")
    item = {"id": ident("deliverable", decision_id + title), "type": "deliverable", "title": title,
            "decision_id": decision_id, "artifact": relative_artifact, "artifact_sha256": actual_hash,
            "artifact_bytes": artifact_path.stat().st_size, "completion_proof": proof,
            "external_verifier_result": verifier_result, "semantic_status": "reported-by-external-verifier", "created_at": now(),
            "source_id": decision.get("source_id"), "provenance": {"origin": "human-approved", "decision_id": decision_id}}
    write_json(root / "data" / "deliverables" / f"{item['id']}.json", item)
    decision["status"] = "completed"
    write_json(root / "data" / "decisions" / f"{decision_id}.json", decision)
    return item


def privacy_check(root: Path) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(?:/Users/|/home/|\\Users\\)[A-Za-z0-9._-]+(?:[/\\][^\s\"']+)?", text):
            violations.append({"path": str(path.relative_to(root)), "rule": "absolute-user-path"})
        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
            violations.append({"path": str(path.relative_to(root)), "rule": "email-address"})
    return {"status": "pass" if not violations else "fail", "violations": violations}


def export_public(root: Path, out: Path, *, include_metadata: bool = False) -> dict[str, Any]:
    """Export counts/types by default; metadata requires an explicit reviewed opt-in."""
    root_resolved = root.resolve()
    out = out.resolve()
    export_root = (root / "data" / "exports").resolve()
    if export_root not in out.parents or out == root_resolved:
        raise ValueError("export output must be a new or existing directory under data/exports")
    out.mkdir(parents=True, exist_ok=True)
    folders = ("writings", "ideas", "hypotheses", "decisions", "workflows", "deliverables", "receipts")
    bundle = {"format": "journaling-door-workflow-export-v1", "exported_at": now(),
              "privacy": {"anonymized": False, "raw_text_included": False, "metadata_included": include_metadata,
                          "metadata_review_required": include_metadata}, "records": {}}
    for folder in folders:
        items = records(root, folder)
        if include_metadata:
            bundle["records"][folder] = [{k: v for k, v in item.items() if k not in {"text"}} for item in items]
        else:
            bundle["records"][folder] = {"count": len(items), "types": sorted({str(item.get("type", folder.rstrip("s"))) for item in items})}
    write_json(out / "manifest.json", bundle)
    return {"path": str(out / "manifest.json"), "record_folders": sorted(bundle["records"]), "raw_text_included": False, "metadata_included": include_metadata}
