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
    def test_separate_sections_never_extend_the_last_paragraph(self):
        body = judg("Judg-1", "1&emsp;First synthetic paragraph.") + judg("Judg-1", "2&emsp;Final synthetic paragraph.")
        for title in ("Annexes", "Annex 1: History", "Appendix A", "Appendices", "Annexure 1", "Schedule 1", "Attachment A"):
            for signature in ("", judg("Judg-Sign", "Synthetic Judge")):
                page = body + signature + judg("Judg-Heading-1", title) + judg("Judg-Quote-List", "A.1 Synthetic annex only.")
                with self.subTest(title=title, signature=bool(signature)):
                    result = r.converters.extract_elitigation(page)
                    self.assertEqual(result["opinions"][0]["text"], "[1] First synthetic paragraph.\n[2] Final synthetic paragraph.\n")
                    self.assertTrue(any("A.1 Synthetic annex only." == b["text"] for b in result["trailing"]))
                    self.assertTrue(any("separate section" in w for w in result["report"]["warnings"]))
                    self.assertEqual(sum(result["report"]["block_counts"].values()), sum(result["report"]["source_block_classes"].values()))

    def test_signature_requires_new_author_to_resume_body(self):
        page = (judg("Judg-1", "1&emsp;Majority.") + judg("Judg-Sign", "Synthetic Judge A")
                + judg("Judg-1", "1&emsp;Ambiguous trailing number.")
                + judg("Judg-Author", "Synthetic Judge B (dissenting):")
                + judg("Judg-1", "1&emsp;Dissent.") + judg("Judg-1", "A dissent continuation."))
        result = r.converters.extract_elitigation(page)
        self.assertEqual([o["text"] for o in result["opinions"]], ["[1] Majority.\n", "[1] Dissent.\nA dissent continuation.\n"])
        self.assertTrue(any("Ambiguous trailing number." in b["text"] for b in result["trailing"]))

    def test_ordinary_headings_do_not_terminate_opinion(self):
        result = r.converters.extract_elitigation(judg("Judg-1", "1&emsp;First.")
            + judg("Judg-Heading-1", "Conclusion") + judg("Judg-1", "2&emsp;Second.")
            + judg("Judg-Quote-0", "A genuine quoted continuation."))
        self.assertIn("[2] Second.\n    A genuine quoted continuation.", result["opinions"][0]["text"])

    def test_annex_overview_inside_numbered_body_is_not_an_annex(self):
        page = (judg("Judg-1", "9&emsp;Body.") + judg("Judg-Heading-1", "Annexes")
                + judg("Judg-1", "10&emsp;I describe the annexes here.")
                + judg("Judg-Heading-1", "Background") + judg("Judg-1", "11&emsp;More body.")
                + judg("Judg-Heading-1", "Annex 1: Details")
                + judg("Judg-Quote-List", "A.1 Actual synthetic annex."))
        result = r.converters.extract_elitigation(page)
        self.assertEqual(result["opinions"][0]["text"], "[9] Body.\n[10] I describe the annexes here.\n[11] More body.\n")
        self.assertEqual(result["trailing"][-1]["text"], "A.1 Actual synthetic annex.")

    def test_unsupported_numbered_section_without_heading_is_quarantined(self):
        result = r.converters.extract_elitigation(judg("Judg-1", "1&emsp;Body.")
            + judg("Judg-Quote-List", "A.1 Separate synthetic analysis."))
        self.assertEqual(result["opinions"][0]["text"], "[1] Body.\n")
        self.assertTrue(any("unsupported section numbering" in w for w in result["report"]["warnings"]))

    def test_unknown_blocks_are_preserved_and_reported(self):
        result = r.converters.extract_elitigation(judg("Judg-1", "1&emsp;Body.")
            + judg("Judg-Unfamiliar", "Synthetic unfamiliar material."))
        self.assertEqual(result["report"]["block_counts"]["unrecognised"], 1)
        self.assertEqual(result["trailing"][0]["text"], "Synthetic unfamiliar material.")
        self.assertTrue(any("unrecognised" in w for w in result["report"]["warnings"]))

    def test_size_diagnostic_does_not_truncate_a_valid_long_paragraph(self):
        long = "Synthetic lengthy reasoning. " * 150
        result = r.converters.extract_elitigation(judg("Judg-1", "1&emsp;Short.") + judg("Judg-1", "2&emsp;" + long))
        self.assertIn(long.strip(), result["opinions"][0]["text"])
        self.assertTrue(any("unusually large" in w for w in result["report"]["warnings"]))

    def test_cli_retains_trailing_material_and_rejects_colliding_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "page.html"
            page.write_text(judg("Judg-1", "1&emsp;Body.") + judg("Judg-Heading-1", "Annex 1")
                            + judg("Judg-Quote-List", "A.1 Synthetic annex text."), encoding="utf-8")
            out = Path(folder) / "body.txt"
            with self.assertRaisesRegex(ValueError, "distinct"):
                r.extract_elitigation_page(page, out, trailing_out=out)
            self.assertFalse(out.exists())
            result = r.extract_elitigation_page(page, out)
            self.assertEqual(out.read_text(encoding="utf-8"), "[1] Body.\n")
            self.assertIn("A.1 Synthetic annex text.", Path(result["trailing_file"]).read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                r.extract_elitigation_page(page, out)

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
