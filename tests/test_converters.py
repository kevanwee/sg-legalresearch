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


SSO = ('<html><head><title>\n Synthetic Act 2099 - Singapore Statutes Online\n</title></head><body>'
       '<nav>Home Browse</nav><div class="status">Status: Not current version (effective from 01 Jan 2099 '
       'to 02 Feb 2099) Print Select the provisions</div>'
       '<div class="versions">03 Mar 2099 Amended by Act 9 of 2099 01 Jan 2099 Act 1 of 2099</div>'
       '<div id="legisContent"><div class="prov1"><table><tr><td class="prov1Hdr">Synthetic heading</td></tr>'
       '<tr><td class="prov1Txt"><strong>12.</strong>—(1)  Synthetic rule applies if —'
       '<table><tr><td>(</td><td>a</td><td>)</td><td>the first synthetic condition; or</td></tr>'
       '<tr><td>(</td><td>b</td><td>)</td><td>the second synthetic condition.</td></tr></table>'
       '</td></tr><tr><td>(2)  A second synthetic subsection.</td></tr></table></div></div>'
       '<div class="footer">Singapore Statutes Online FAQs Feedback</div></body></html>')


class SsoTests(unittest.TestCase):
    def test_provision_text_and_version_evidence(self):
        result = r.converters.extract_sso(SSO)
        self.assertEqual(result["text"], "Synthetic heading\n12.—(1) Synthetic rule applies if —\n"
                                         "(a)\nthe first synthetic condition; or\n(b)\nthe second synthetic condition.\n"
                                         "(2) A second synthetic subsection.\n")
        self.assertEqual(result["title"], "Synthetic Act 2099")
        self.assertEqual(result["status"], "Not current version (effective from 01 Jan 2099 to 02 Feb 2099)")
        self.assertEqual(result["act_amendments"], [{"date": "03 Mar 2099", "by": "Act 9 of 2099"}])
        self.assertEqual((result["provisions"], result["warnings"]), (["12"], []))
        self.assertNotIn("FAQs", result["text"])

    def test_converted_text_supports_a_provision_map(self):
        text = r.converters.extract_sso(SSO)["text"]
        rows = [("s 12", "12.—", None), ("s 12(1)", "(1) Synthetic", "(2) A second"),
                ("s 12(1)(a)", "(a)", "(b)"), ("s 12(1)(b)", "(b)", "(2) A second")]
        provisions = [{"locator": loc, "start": text.index(a), "end": text.index(b) if b else len(text),
                       "status": "in-force", "status_note": "Synthetic fixture."} for loc, a, b in rows]
        self.assertEqual(len(r.build_provisions(text, {"provisions": provisions})), 4)

    def test_missing_content_is_refused_and_missing_status_warned(self):
        with self.assertRaisesRegex(ValueError, "legisContent"):
            r.converters.extract_sso("<html><body>Search page</body></html>")
        no_status = SSO.replace("Status: ", "")
        self.assertTrue(any("status" in w for w in r.converters.extract_sso(no_status)["warnings"]))

    def test_cli_reports_status_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "act.html"
            page.write_text(SSO, encoding="utf-8")
            args = [sys.executable, "-I", str(SCRIPT), "extract-sso", str(page), "--out", str(Path(folder) / "act.txt")]
            done = subprocess.run(args, capture_output=True, cwd=folder)
            self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", "replace"))
            self.assertTrue(json.loads(done.stdout.decode("utf-8"))["status"].startswith("Not current version"))
            self.assertEqual(subprocess.run(args, capture_output=True, cwd=folder).returncode, 2)


if __name__ == "__main__":
    unittest.main()
