#!/usr/bin/env python3
"""Install portable skills into an explicit project-local directory."""
from pathlib import Path
import argparse
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("destination", help="Explicit destination, such as .agents/skills or .claude/skills")
parser.add_argument("--source", help="Skill root; defaults to this repository's skills directory")
parser.add_argument("--apply", action="store_true", help="Copy files; without this flag only preview")
args = parser.parse_args()
repo_root = Path(__file__).resolve().parents[1]
source = (Path(args.source) if args.source else repo_root / "skills").resolve()
destination = Path(args.destination).resolve()
files = sorted(source.glob("*/SKILL.md"))
if not files:
    raise SystemExit(f"No skill folders containing SKILL.md found under {source}")
conflicts = [destination / path.parent.name / path.name for path in files if (destination / path.parent.name / path.name).exists()]
print(f"source={source}\ndestination={destination}\nfiles={len(files)}\nconflicts={len(conflicts)}")
if conflicts:
    raise SystemExit("Refusing to overwrite existing skill files: " + ", ".join(str(p) for p in conflicts))
if not args.apply:
    print("dry-run: pass --apply to copy into this explicit destination")
    raise SystemExit(0)
destination.mkdir(parents=True, exist_ok=True)
for path in files:
    target = destination / path.parent.name / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
print(f"installed={len(files)}")
