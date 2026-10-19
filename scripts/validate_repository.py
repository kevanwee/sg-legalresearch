#!/usr/bin/env python3
"""Offline packaging and relative-link checks; no third-party dependencies."""

import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def validate():
    errors = []
    for path in ROOT.rglob("*.py"):
        if any(p in (".local", ".venv", ".git") for p in path.relative_to(ROOT).parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    for path in ROOT.rglob("*.md"):
        if any(p in (".local", ".venv", ".git") for p in path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]\n]*\]\(([^\s]+?)\)", text):
            if target.startswith(("http:", "https:", "mailto:", "#")):
                continue
            filename, _, anchor = target.partition("#")
            dest = (path.parent / unquote(filename)).resolve()
            if not dest.is_relative_to(ROOT) or not dest.is_file():
                errors.append(f"{path.relative_to(ROOT)}: missing or external local link {target}")
            elif anchor and dest.suffix == ".md":
                headings = re.findall(r"^#{1,6}\s+(.+)$", dest.read_text(encoding="utf-8"), re.M)
                slugs = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in headings}
                if anchor not in slugs:
                    errors.append(f"{path.relative_to(ROOT)}: missing anchor {target}")
        if text.count("```") % 2:
            errors.append(f"{path.relative_to(ROOT)}: unclosed code fence")
    skill = ROOT / "skills/singapore-legal-research/SKILL.md"
    text = skill.read_text(encoding="utf-8")
    front = text.split("---", 2)
    if len(front) != 3 or not text.startswith("---\n"):
        errors.append("skill frontmatter missing")
    else:
        fields = dict(line.split(":", 1) for line in front[1].strip().splitlines() if ":" in line)
        if fields.get("name", "").strip() != skill.parent.name or not fields.get("description", "").strip():
            errors.append("skill name or description invalid")
    if re.search(r"\bTODO\b|\[INSERT|\[PLACEHOLDER", text):
        errors.append("unfinished skill scaffold")
    for path in (ROOT / "skills").rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
    metadata = skill.parent / "agents/openai.yaml"
    if "$singapore-legal-research" not in metadata.read_text(encoding="utf-8"):
        errors.append("UI prompt must invoke the skill")
    print("\n".join(errors) if errors else "Repository checks passed: Python syntax, skill metadata, fences and relative links.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(validate())
