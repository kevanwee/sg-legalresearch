"""Synthetic page fixtures only: they imitate page structure and contain no real judgments or law."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/singapore-legal-research/scripts/research.py"
spec = importlib.util.spec_from_file_location("converter_research", SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def judg(cls, text):
    return f'<div class="{cls} mb-3 text-justify  ">{text}</div>'


def note(n, text):
    return (f"<sup><button type='button' class='btn btn-link superscript-btn'>{n}</button></sup>"
            f"<div class='modal fade' role='dialog'><div class='modal-dialog'><div class='modal-content'>"
            f"<div class='modal-header'><h5 class='modal-title'>Foot Note {n}</h5></div>"
            f"<div class='modal-body'><div class=\"FootnoteRef text-justify  \"> &emsp;{text}</div></div>"
            f"</div></div></div>")


ELIT = ('<html><body><div class="HN-CaseName text-center font-weight-bold ">Synthetic Alpha Pte Ltd '
        '<span class="font-italic">v</span> Synthetic Beta Pte Ltd [2099] SGCA 1</div>'
        + judg("Judg-Date-Reserved", "1 January 2099 Judgment reserved.")
        + judg("Judg-Author", "Synthetic Judge A (delivering the majority judgment):")
        + judg("Judg-Heading-1", "Synthetic heading")
        + judg("Judg-1", "1&emsp;First synthetic paragraph." + note(1, "Synthetic note text only.") + " Continues.")
        + judg("Judg-1", "")
        + judg("Judg-1", "An unnumbered synthetic continuation.")
        + judg("Judg-Quote-0", "A synthetic quotation.")
        + judg("Judg-2", "(a) a synthetic sub-paragraph;")
        + judg("Judg-1", "2&emsp;Second synthetic paragraph.")
        + judg("Judg-Sign", "Synthetic Judge A")
        + judg("Judg-Author", "Synthetic Judge B (dissenting):")
        + judg("Judg-1", "1&emsp;First synthetic dissent paragraph.")
        + judg("Judg-1", "2&emsp;Second synthetic dissent paragraph.")
        + judg("Judg-Lawyers", "Synthetic counsel for the parties.")
        + judg("Judg-EOF", "[End of document]") + "</body></html>")


class ElitigationTests(unittest.TestCase):
    def test_structure_notes_and_separate_opinions(self):
        result = r.converters.extract_elitigation(ELIT)
        self.assertEqual(result["header"], "Synthetic Alpha Pte Ltd v Synthetic Beta Pte Ltd [2099] SGCA 1")
        majority, dissent = result["opinions"]
        self.assertEqual(majority["text"], "[1] First synthetic paragraph.[note: 1] Continues.\n"
                                           "An unnumbered synthetic continuation.\n    A synthetic quotation.\n"
                                           "(a) a synthetic sub-paragraph;\n[2] Second synthetic paragraph.\n")
        self.assertTrue(majority["author"].startswith("Synthetic Judge A"))
        self.assertEqual((dissent["first"], dissent["last"]), (1, 2))
        self.assertNotIn("Synthetic note text", majority["text"])
        self.assertNotIn("Synthetic counsel", dissent["text"] + majority["text"])
        self.assertEqual(result["notes"], ["[note: 1] Synthetic note text only."])
        report = result["report"]
        self.assertEqual((report["html_numbered_blocks"], report["extracted_paragraphs"]), (4, 4))
        self.assertEqual(report["spacer_blocks"], 1)
        self.assertEqual(report["warnings"], [])
        for opinion in result["opinions"]:
            self.assertEqual(len(r.build_paragraphs(opinion["text"], "bracketed")), 2)

    def test_gap_and_restart_are_reported(self):
        gap = judg("Judg-Author", "Synthetic Judge:") + judg("Judg-1", "1&emsp;One.") + judg("Judg-1", "3&emsp;Three.")
        self.assertTrue(any("numbering gap" in w for w in r.converters.extract_elitigation(gap)["report"]["warnings"]))
        restart = judg("Judg-1", "1&emsp;One.") + judg("Judg-1", "2&emsp;Two.") + judg("Judg-1", "1&emsp;Again.")
        result = r.converters.extract_elitigation(restart)
        self.assertEqual(len(result["opinions"]), 2)
        self.assertTrue(any("restarted" in w for w in result["report"]["warnings"]))

    def test_page_without_numbered_paragraphs_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no numbered judgment paragraphs"):
            r.converters.extract_elitigation("<html><body><p>Not a judgment.</p></body></html>")

    def test_cli_writes_each_opinion_and_notes_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "judgment.html"
            page.write_text(ELIT, encoding="utf-8")
            args = [sys.executable, "-I", str(SCRIPT), "extract-elitigation", str(page), "--out", str(Path(folder) / "j.txt")]
            done = subprocess.run(args, capture_output=True, cwd=folder)
            self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", "replace"))
            output = json.loads(done.stdout.decode("utf-8"))
            self.assertEqual([Path(o["file"]).name for o in output["opinions"]], ["j-opinion-1.txt", "j-opinion-2.txt"])
            self.assertEqual(Path(output["notes_file"]).read_text(encoding="utf-8"), "[note: 1] Synthetic note text only.\n")
            self.assertEqual(subprocess.run(args, capture_output=True, cwd=folder).returncode, 2)


if __name__ == "__main__":
    unittest.main()
