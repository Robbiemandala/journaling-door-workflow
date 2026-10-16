# Portable architecture

This repository is a clean-room, reduced-surface implementation of mechanisms observed in the source Journaling Door and Robbie OS repositories. It uses generic relative names so the portable copy contains no personal paths or identity data.

| Portable component | Mechanism carried forward | Deliberate reduction |
| --- | --- | --- |
| `data/transcripts/` and `data/writings/` | Preserve original capture and a linked, readable writing record | JSON instead of a full Markdown/YAML vault |
| `data/ideas/` and `data/hypotheses/` | Keep human ideas distinct from agent-generated findings with source lineage | No model API or semantic sweep |
| `duplicate_review` and recurrence fields | Exact/probable repeats remain reviewable; recurrence evidence does not inflate patterns | No audio or inbox harvester |
| `build_patterns` and `search` | Deterministic navigation by token and source root | No SQLite/FTS index or browser dashboard |
| `decide` | Human decision, explicit target, completion proof, and bounded active work | Three-item default WIP limit rather than a configurable personal policy |
| `plan_workflow`, `record_run`, `verify_workflow` | Scout → worker → verifier DAG, honest model routing, local evidence receipts, staleness checks | No native team launcher; real agents remain an external caller |
| `record_deliverable` | Delivery binds to a verified worker hash and requires a separately supplied semantic verifier result | Integrity checks do not establish semantic truth; no publication, deployment, or external integrations |

The source repositories remain read-only references. This implementation intentionally omits private records, transcript examples, runtime ledgers, personal configuration, and global skill installation. A plan or receipt is evidence of local bookkeeping; it is not evidence that Codex or Claude actually ran unless a real runner wrote the referenced artifact and recorded the receipt.
