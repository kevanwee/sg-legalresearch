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
