"""Exercise copied installations and CLI behaviour in isolated temporary folders."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install_skill.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PackagingTests(unittest.TestCase):
    def test_install_is_self_contained_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = installer.install("codex", Path(folder) / "skills")
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertTrue((destination / "references/statutes-revised-editions.md").is_file())
            script = destination / "scripts/research.py"
            run = Path(folder) / "private-run"
            args = [sys.executable, str(script), "init", str(run), "--question", "Synthetic question",
                    "--research-date", "2026-10-20", "--law-as-at", "2026-10-20"]
            completed = subprocess.run(args, capture_output=True, text=True, cwd=folder)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((run / "run.json").is_file())
            checked = subprocess.run([sys.executable, str(script), "check", str(run)],
                                     capture_output=True, text=True, cwd=folder)
            self.assertEqual(checked.returncode, 1)
            self.assertEqual(json.loads(checked.stdout)["status"], "fail")
            source = Path(folder) / "judgment.txt"
            source.write_text("[1] Synthetic first paragraph.\n[2] Synthetic second paragraph.", encoding="utf-8")
            snapshot = subprocess.run([sys.executable, str(script), "snapshot", str(run), str(source),
                "--id", "S1", "--kind", "case", "--title", "Synthetic case", "--url", "https://example.invalid/case",
                "--citation", "SYNTHETIC-1", "--version", "test fixture"], capture_output=True, text=True, cwd=folder)
            self.assertEqual(snapshot.returncode, 0, snapshot.stderr)
            index_args = [sys.executable, str(script), "index-paragraphs", str(run), "--source", "S1",
                          "--style", "bracketed", "--review-note", "Synthetic boundaries checked."]
            not_confirmed = subprocess.run(index_args, capture_output=True, text=True, cwd=folder)
            self.assertNotEqual(not_confirmed.returncode, 0)
            indexed = subprocess.run(index_args + ["--confirm-boundaries"], capture_output=True, text=True, cwd=folder)
            self.assertEqual(indexed.returncode, 0, indexed.stderr)
            packet = subprocess.run([sys.executable, str(script), "passages", str(run), "--source", "S1",
                                     "--pinpoint", "[1]-[2]"], capture_output=True, text=True, cwd=folder)
            self.assertEqual(packet.returncode, 0, packet.stderr)
            self.assertEqual(len(json.loads(packet.stdout)["evidence"]["passages"]), 2)
            again = subprocess.run(args, capture_output=True, text=True, cwd=folder)
            self.assertEqual(again.returncode, 2)
            with self.assertRaises(FileExistsError):
                installer.install("codex", Path(folder) / "skills")

    def test_claude_install_copies_same_skill(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = installer.install("claude", Path(folder))
            self.assertEqual(destination.name, "singapore-legal-research")
            self.assertTrue((destination / "agents/openai.yaml").is_file())

    def test_invalid_target_is_rejected(self):
        with self.assertRaises(ValueError):
            installer.install("unknown")

    def test_repository_validation(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_repository.py")],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
