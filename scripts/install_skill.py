#!/usr/bin/env python3
"""Copy this repository's skill to a discovery directory without overwriting."""

import argparse
from pathlib import Path
import shutil
import sys


def install(target, skills_dir=None):
    if target not in ("codex", "claude"):
        raise ValueError("target must be codex or claude")
    source = Path(__file__).resolve().parents[1] / "skills" / "singapore-legal-research"
    parent = (Path(skills_dir).expanduser() if skills_dir else
              Path.home() / (".agents" if target == "codex" else ".claude") / "skills")
    destination = parent / source.name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Installation already exists: {destination}. Review it before replacing.")
    parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=("codex", "claude"))
    parser.add_argument("--skills-dir", type=Path, help="override the skill discovery directory")
    args = parser.parse_args()
    try:
        print(f"Installed: {install(args.target, args.skills_dir)}")
        print("Start a new session to discover the skill.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
