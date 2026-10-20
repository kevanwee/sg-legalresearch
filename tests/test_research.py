"""Synthetic fixtures only: these are not Singapore authorities or legal advice."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/singapore-legal-research/scripts/research.py"
spec = importlib.util.spec_from_file_location("research", SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def make_docx(path, body=None):
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = body or ('<w:p><w:r><w:t>Synthetic body.</w:t><w:footnoteReference w:id="7"/></w:r></w:p>'
                    '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table authority.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document {ns}><w:body>{body}</w:body></w:document>')
        z.writestr("word/footnotes.xml", f'<w:footnotes {ns}>'
                   '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:t>Do not inventory.</w:t></w:r></w:p></w:footnote>'
                   '<w:footnote w:id="7"><w:p><w:r><w:t>Synthetic footnote.</w:t></w:r></w:p></w:footnote>'
                   '</w:footnotes>')
        z.writestr("word/endnotes.xml", f'<w:endnotes {ns}><w:endnote w:id="3"><w:p><w:r>'
                   '<w:t>Synthetic endnote.</w:t></w:r></w:p></w:endnote></w:endnotes>')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.run = self.base / "run"
        r.init_run(self.run, "Synthetic research question", "research", "2026-10-20", "2026-10-20")
        self.file = self.base / "source.txt"
        self.file.write_text("[1] A synthetic proposition.\n[2] A second sentence.", encoding="utf-8")
        r.snapshot(self.run, self.file, "S1", "Synthetic source — not law", "other",
                   "https://example.invalid/source", "SYNTHETIC-1", "test version")
        self.data = r.load_run(self.run)
        self.data["review"] = "Same-agent synthetic test review."
        self.data["sources"][0].update(identity_verified=True, full_text_reviewed=True,
            publication_authority="Synthetic test fixture only", review_note="Reviewed fixture.",
            retrieved_on="2026-10-20")
        self.data["claims"] = [{"id": "C1", "text": "A synthetic proposition.",
            "location": "answer/p:1", "assessment": "supported", "reason": "Fixture asserts these words.",
            "evidence": [{"source_id": "S1", "pinpoint": "[1]", "pinpoint_reviewed": True,
                          "support_note": "Test-only passage."}]}]

    def save(self):
        r.write_json(self.run / "run.json", self.data)

    def report(self):
        self.save()
        return r.check_run(self.run)

    def case_source(self):
        source = self.data["sources"][0]
        text = self.file.read_text(encoding="utf-8")
        source.update(kind="case", paragraph_index={"style": "bracketed", "text_sha256": source["text_sha256"],
            "boundaries_reviewed": True, "review_note": "Synthetic paragraph boundaries checked.",
            "paragraphs": r.build_paragraphs(text, "bracketed")})
        source["treatment"] = {"status": "not-checked", "note": "Synthetic fixture; no real treatment search.", "search_ids": []}
        self.data["claims"][0]["evidence"][0]["passages"] = r.select_paragraphs(source["paragraph_index"]["paragraphs"], "[1]")
        return source

    def test_reviewed_record_passes(self):
        self.assertEqual(self.report()["status"], "pass-record-checks")

    def test_init_does_not_overwrite(self):
        with self.assertRaises(FileExistsError):
            r.init_run(self.run, "new", "research", "2026-10-20", "2026-10-20")

    def test_stale_temporary_file_does_not_block_writes(self):
        (self.run / "run.json.tmp").write_text("interrupted", encoding="utf-8")
        self.assertEqual(self.report()["status"], "pass-record-checks")
        self.assertFalse((self.run / "run.json.tmp").exists())

    def test_empty_run_cannot_pass(self):
        other = self.base / "empty"
        r.init_run(other, "Synthetic question", "research", "2026-10-20", "2026-10-20")
        self.assertEqual(r.check_run(other)["status"], "fail")

    def test_source_tampering_is_detected(self):
        p = r.inside(self.run, self.data["sources"][0]["file"])
        p.write_text("Altered evidence", encoding="utf-8")
        self.assertTrue(any("hash mismatch" in e for e in self.report()["errors"]))

    def test_path_escape_is_rejected(self):
        self.data["sources"][0]["text_file"] = "../source.txt"
        self.assertTrue(any("escapes" in e for e in self.report()["errors"]))

    def test_support_cannot_rely_on_unreviewed_source(self):
        self.data["sources"][0]["full_text_reviewed"] = False
        self.assertTrue(any("unreviewed source" in e for e in self.report()["errors"]))

    def test_truthy_string_is_not_review(self):
        self.data["sources"][0]["identity_verified"] = "true"
        self.assertEqual(self.report()["status"], "fail")

    def test_pinpoint_must_be_reviewed(self):
        self.data["claims"][0]["evidence"][0]["pinpoint_reviewed"] = False
        self.assertEqual(self.report()["status"], "fail")

    def test_unknown_evidence_reference(self):
        self.data["claims"][0]["evidence"][0]["source_id"] = "missing"
        self.assertEqual(self.report()["status"], "fail")

    def test_duplicate_claim_ids(self):
        self.data["claims"].append(copy.deepcopy(self.data["claims"][0]))
        self.assertTrue(any("duplicate id" in e for e in self.report()["errors"]))

    def quote(self, text="A synthetic proposition.", start=4, end=28):
        # [1] + space = 4 characters; sentence length is 24.
        return {"id": "Q1", "claim_id": "C1", "source_id": "S1", "text": text,
                "start": start, "end": end, "pinpoint": "[1]", "pinpoint_reviewed": True}

    def test_exact_quote_passes(self):
        self.data["quotes"] = [self.quote()]
        self.assertEqual(self.report()["status"], "pass-record-checks")

    def test_invented_quote_fails(self):
        self.data["quotes"] = [self.quote("A binding legal proposition.")]
        self.assertTrue(any("does not match" in e for e in self.report()["errors"]))

    def test_case_changes_are_not_silently_normalised(self):
        self.data["quotes"] = [self.quote("a synthetic proposition.")]
        self.assertEqual(self.report()["status"], "fail")

    def test_quote_outside_claim_pinpoint_fails(self):
        q = self.quote()
        q["pinpoint"] = "[2]"
        self.data["quotes"] = [q]
        self.assertTrue(any("linked to its claim" in e for e in self.report()["errors"]))

    def test_quote_bad_span_fails(self):
        self.data["quotes"] = [self.quote(start=-1)]
        self.assertTrue(any("invalid character span" in e for e in self.report()["errors"]))

    def test_unresolved_is_disclosed_as_limit(self):
        self.data["claims"][0].update(assessment="unresolved", evidence=[], reason="Source inaccessible.")
        report = self.report()
        self.assertEqual(report["status"], "pass-with-limits")
        self.assertTrue(any("unresolved" in e for e in report["limits"]))

    def test_legislation_needs_version_review(self):
        self.data["sources"][0]["kind"] = "legislation"
        self.assertTrue(any("version_review" in e for e in self.report()["errors"]))

    def test_public_search_is_limited(self):
        s = self.case_source()
        s.update(kind="case", treatment={"status": "public-search-limited",
            "note": "Synthetic searches only; no citator.", "search_ids": ["T1"]})
        self.data["search_log"] = [{"id": "T1", "database": "Synthetic database",
            "query": "SYNTHETIC-1", "coverage": "Synthetic fixture only", "result_note": "No matches in fixture.",
            "searched_on": "2026-10-20"}]
        self.assertEqual(self.report()["status"], "pass-with-limits")

    def test_treatment_claim_needs_search_evidence(self):
        self.case_source().update(treatment={"status": "citator-checked",
            "note": "Unsupported claim of citator use", "search_ids": []})
        self.assertEqual(self.report()["status"], "fail")

    def test_malformed_arrays_fail(self):
        self.data["claims"] = {}
        self.assertEqual(self.report()["status"], "fail")

    def test_derived_text_requires_conversion_receipt(self):
        with self.assertRaisesRegex(ValueError, "transformation"):
            r.snapshot(self.run, self.file, "S2", "Synthetic", "other", "https://example.invalid",
                       "SYNTHETIC-2", "test", self.file)

    def test_source_id_cannot_escape(self):
        with self.assertRaises(ValueError):
            r.snapshot(self.run, self.file, "../S2", "Synthetic", "other", "https://example.invalid", "id", "test")

    def test_full_case_paragraph_is_required_even_for_a_paraphrase(self):
        self.case_source()
        self.assertFalse(self.report()["errors"])
        del self.data["claims"][0]["evidence"][0]["passages"]
        self.assertTrue(any("every full cited paragraph" in e for e in self.report()["errors"]))

    def test_quote_from_different_paragraph_is_rejected(self):
        self.case_source()
        text = self.file.read_text(encoding="utf-8")
        words = "A second sentence."
        start = text.index(words)
        self.data["quotes"] = [self.quote(words, start, start + len(words))]
        self.assertTrue(any("outside the full paragraphs" in e for e in self.report()["errors"]))

    def test_case_quote_within_cited_paragraph_passes(self):
        self.case_source()
        self.data["quotes"] = [self.quote()]
        self.assertFalse(self.report()["errors"])

    def test_disjoint_citation_does_not_cover_intervening_paragraph(self):
        source = self.case_source()
        # Extend the synthetic source fixture before assembling this test's evidence.
        path = r.inside(self.run, source["file"])
        text = path.read_text(encoding="utf-8") + "\n[3] A third sentence."
        path.write_text(text, encoding="utf-8")
        source["sha256"] = source["text_sha256"] = r.digest(path)
        source["paragraph_index"].update(text_sha256=source["text_sha256"], paragraphs=r.build_paragraphs(text, "bracketed"))
        ref = self.data["claims"][0]["evidence"][0]
        ref.update(pinpoint="[1], [3]", passages=r.select_paragraphs(source["paragraph_index"]["paragraphs"], "[1], [3]"))
        self.data["quotes"] = [dict(self.quote(text[4:], 4, len(text)), pinpoint="[1], [3]")]
        self.assertTrue(any("outside the full paragraphs" in e for e in self.report()["errors"]))

    def test_captured_passage_cannot_relabel_another_paragraph(self):
        source = self.case_source()
        bad = copy.deepcopy(source["paragraph_index"]["paragraphs"][1])
        bad["paragraph"] = 1
        self.data["claims"][0]["evidence"][0]["passages"] = [bad]
        self.assertTrue(any("every full cited paragraph" in e for e in self.report()["errors"]))

    def test_index_cannot_be_rewritten_to_match_a_wrong_pinpoint(self):
        source = self.case_source()
        source["paragraph_index"]["paragraphs"][0]["text"] = "Made up paragraph."
        self.assertTrue(any("does not match source paragraph labels" in e for e in self.report()["errors"]))

    def test_paragraph_range_captures_every_full_paragraph(self):
        self.case_source()
        self.save()
        packet = r.capture_passages(self.run, "S1", "[1]-[2]")
        self.assertEqual([p["paragraph"] for p in packet["evidence"]["passages"]], [1, 2])
        self.assertTrue(packet["citation"].endswith("at [1]–[2]"))
        self.assertIs(packet["evidence"]["pinpoint_reviewed"], False)

    def test_missing_paragraph_and_overbroad_range_fail(self):
        source = self.case_source()
        for pin in ("[3]", "[1]–[3]", "[1]–[999999999]"):
            with self.subTest(pin=pin), self.assertRaisesRegex(ValueError, "missing"):
                r.select_paragraphs(source["paragraph_index"]["paragraphs"], pin)

    def test_extraction_requires_explicit_reviewed_boundaries(self):
        source = self.case_source()
        source["paragraph_index"]["boundaries_reviewed"] = False
        self.assertTrue(any("reviewed boundaries" in e for e in self.report()["errors"]))

    def test_paragraph_cli_can_index_numbered_source_text(self):
        self.save()
        r.index_paragraphs(self.run, "S1", "bracketed", "Synthetic labels checked.")
        self.assertEqual(len(r.capture_passages(self.run, "S1", "at [1], [2]")["evidence"]["passages"]), 2)
        numbered = r.build_paragraphs("35\tFirst line.\nContinuation.\n36\u2003Second paragraph.", "numbered")
        self.assertEqual(numbered[0]["text"], "First line.\nContinuation.")
        self.assertEqual(numbered[1]["paragraph"], 36)

    def test_ambiguous_numbering_and_malformed_pinpoints_fail(self):
        for text in ("[1] First\n[1] Repeated", "[2] First\n[1] Reverse", "No labels", "[1] First\n[1A] Lettered"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                r.build_paragraphs(text, "bracketed")
        for pin in ("[2]-[1]", "35", "[0]", "[35A]", "[1] garbage", ""):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                r.parse_pinpoint(pin)

    def test_trailing_note_blocks_are_refused_instead_of_absorbed(self):
        for style, body in (("bracketed", "[1] First.\n[2] Final paragraph."),
                            ("numbered", "1 First.\n2 Final paragraph.")):
            for note in ("Footnotes\n1. Synthetic note text.", "ENDNOTES:\n1. Synthetic note text.",
                         "Notes\nSynthetic note text.", "[note: 1] Synthetic note text.",
                         "[fn 1] Synthetic note text.", "Footnote 1: Synthetic note text."):
                for newline in ("\n", "\r\n"):
                    text = (body + "\n" + note).replace("\n", newline)
                    with self.subTest(style=style, note=note, newline=newline), self.assertRaisesRegex(ValueError, "separate footnote/endnote block"):
                        r.build_paragraphs(text, style)

    def test_inline_note_reference_is_not_a_note_block(self):
        rows = r.build_paragraphs("[1] Reasoning [note: 1] continues.\n[2] Final paragraph.", "bracketed")
        self.assertEqual(rows[0]["text"], "Reasoning [note: 1] continues.")

    def test_prose_mentioning_a_footnote_is_not_a_note_block(self):
        text = "[1] The respondent relied on\nFootnote 3 of the synthetic submissions.\n[2] Final paragraph."
        rows = r.build_paragraphs(text, "bracketed")
        self.assertIn("Footnote 3 of the synthetic submissions.", rows[0]["text"])

    def test_old_index_with_absorbed_note_is_rejected(self):
        source = self.case_source()
        path = r.inside(self.run, source["file"])
        text = self.file.read_text(encoding="utf-8") + "\n[note: 1] Synthetic note only."
        path.write_text(text, encoding="utf-8")
        source["sha256"] = source["text_sha256"] = r.digest(path)
        source["paragraph_index"]["text_sha256"] = source["text_sha256"]
        last = source["paragraph_index"]["paragraphs"][-1]
        last.update(end=len(text), text=text[last["start"]:])
        report = self.report()
        self.assertTrue(any("separate footnote/endnote block" in e for e in report["errors"]))

    def test_missing_middle_label_and_spurious_number_are_rejected(self):
        examples = [
            ("bracketed", "[1] First paragraph.\nSecond paragraph without its label.\n[3] Third paragraph."),
            ("numbered", "35 First paragraph.\nNext paragraph without its label.\n37 Third paragraph."),
            ("bracketed", "[1] First paragraph.\n[2] Second paragraph.\n[100] Spurious number."),
            ("numbered", "35 First paragraph.\n36 Second paragraph.\n100 Spurious number."),
        ]
        for style, text in examples:
            with self.subTest(style=style, text=text), self.assertRaisesRegex(ValueError, "must be consecutive"):
                r.build_paragraphs(text, style)

    def test_bare_labels_cannot_be_merged_into_previous_paragraph(self):
        for style, first, bare, last in (("bracketed", "[1]", "[2]", "[3]"), ("numbered", "35", "36", "37"),
                                        ("bracketed", "[1]", "2", "[3]"), ("numbered", "35", "[36]", "37")):
            for ending in ("\n", "\r\n"):
                examples = [
                    first + " First paragraph." + ending + bare + ending + "Second paragraph." + ending + last + " Third paragraph.",
                    first + " First paragraph." + ending + bare,
                    first + " First paragraph." + ending + "\u2003" + bare + "\u00a0\t" + ending + "Second paragraph.",
                ]
                for text in examples:
                    with self.subTest(style=style, text=text), self.assertRaisesRegex(ValueError, "on its own line"):
                        r.build_paragraphs(text, style)

    def test_numbered_report_reference_on_wrapped_line_fails_loudly(self):
        text = "35 A wrapped reference to [2017]\n2 SLR 850 continues here.\n36 The next paragraph."
        with self.assertRaisesRegex(ValueError, "must be consecutive"):
            r.build_paragraphs(text, "numbered")

    def test_numbering_restart_requires_separate_opinion_sources(self):
        with self.assertRaisesRegex(ValueError, "must be consecutive"):
            r.build_paragraphs("[1] Majority.\n[2] Majority continues.\n[1] Separate opinion.", "bracketed")
        self.assertEqual(len(r.build_paragraphs("[1] Separate opinion.\n[2] Continued.", "bracketed")), 2)

    def test_reviewed_excerpt_can_start_above_one(self):
        rows = r.build_paragraphs("[35] First captured paragraph.\n[36] Second captured paragraph.", "bracketed")
        self.assertEqual([p["paragraph"] for p in rows], [35, 36])

    def test_old_merged_index_cannot_pass_even_with_boundary_confirmation(self):
        text = "[1] First paragraph.\nMisplaced second paragraph.\n[3] Third paragraph."
        source = self.data["sources"][0]
        path = r.inside(self.run, source["file"])
        path.write_text(text, encoding="utf-8")
        source["sha256"] = source["text_sha256"] = r.digest(path)
        split = text.index("[3]")
        rows = [{"paragraph": 1, "start": 4, "end": split - 1, "text": text[4:split - 1]},
                {"paragraph": 3, "start": split + 4, "end": len(text), "text": text[split + 4:]}]
        source.update(kind="case", paragraph_index={"style": "bracketed", "text_sha256": source["text_sha256"],
            "boundaries_reviewed": True, "review_note": "Prior review declaration cannot override broken numbering.", "paragraphs": rows},
            treatment={"status": "not-checked", "note": "Synthetic fixture.", "search_ids": []})
        self.data["claims"][0]["evidence"][0]["passages"] = [rows[0]]
        words = "Misplaced second paragraph."
        start = text.index(words)
        self.data["quotes"] = [self.quote(words, start, start + len(words))]
        self.assertTrue(any("must be consecutive" in e for e in self.report()["errors"]))

    def test_failed_indexing_does_not_save_a_partial_index(self):
        source = self.data["sources"][0]
        path = r.inside(self.run, source["file"])
        path.write_text("[1] First.\n[3] Third.", encoding="utf-8")
        source["sha256"] = source["text_sha256"] = r.digest(path)
        self.save()
        with self.assertRaisesRegex(ValueError, "must be consecutive"):
            r.index_paragraphs(self.run, "S1", "bracketed", "Checked boundaries.")
        self.assertNotIn("paragraph_index", r.load_run(self.run)["sources"][0])

    def as_cited(self, pin="[1]", status="supported"):
        self.case_source()
        self.data["mode"] = "cite-check"
        citation = "Synthetic case SYNTHETIC-1 at " + pin
        self.data["inventory"] = [{"id": "draft/p:1", "text": "A proposition: " + citation + ".",
                                   "reviewed": True, "claim_ids": ["C1"], "reason": ""}]
        self.data["claims"][0].update(location="draft/p:1", citation_check={"source_id": "S1",
            "citation": citation, "pinpoint": pin, "result": status, "reason": "Synthetic citation review."})

    def test_subparagraph_pinpoints_resolve_to_the_whole_paragraph(self):
        for pin, canonical in (("at [185(b)]", "[185(b)]"), ("[185(a)]–[185(c)]", "[185(a)]–[185(c)]"),
                               ("[12(b)(ii)]", "[12(b)(ii)]"), ("[3(a)] and [5]", "[3(a)], [5]")):
            with self.subTest(pin=pin):
                self.assertEqual(r.canonical_pinpoint(pin), canonical)
        self.assertEqual(r.parse_pinpoint("[185(b)]"), [(185, 185)])
        for pin in ("[185(b]", "[2(a)]-[1(b)]", "[185()]", "[185b]", "[185(c)]–[185(a)]"):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                r.parse_pinpoint(pin)

    def subparagraph_evidence(self, pin):
        ref = copy.deepcopy(self.data["claims"][0]["evidence"][0])
        ref.update(pinpoint=pin, passages=r.select_paragraphs(
            self.data["sources"][0]["paragraph_index"]["paragraphs"], pin), support_note="Synthetic sub-paragraph.")
        return ref

    def test_subparagraph_citation_can_be_verified_in_cite_check(self):
        self.as_cited(pin="[1(b)]")
        self.data["claims"][0]["evidence"] = [self.subparagraph_evidence("[1(b)]")]
        report = self.report()
        self.assertFalse(report["errors"])
        self.assertTrue(any("[1(b)] checked against the full paragraph" in l for l in report["limits"]))

    def test_wrong_subparagraph_is_a_separate_locator(self):
        self.as_cited(pin="[1(b)]")
        self.data["claims"][0]["evidence"] = [self.subparagraph_evidence("[1(a)]")]
        self.assertTrue(any("checked separately from any correction" in e for e in self.report()["errors"]))
        self.as_cited(pin="[1(b)]", status="wrong-pinpoint")
        self.data["claims"][0].update(assessment="qualified", evidence=[self.subparagraph_evidence("[1(b)]"),
                                                                        self.subparagraph_evidence("[1(a)]")])
        self.assertFalse(self.report()["errors"])

    def test_equivalent_range_forms_still_match_without_subparagraphs(self):
        self.as_cited(pin="[1]–[2]")
        self.data["claims"][0]["evidence"] = [self.subparagraph_evidence("[1], [2]")]
        self.assertFalse(self.report()["errors"])

    def test_capture_keeps_the_literal_subparagraph_pinpoint(self):
        self.case_source()
        self.save()
        packet = r.capture_passages(self.run, "S1", "at [1(b)]")
        self.assertEqual(packet["evidence"]["pinpoint"], "[1(b)]")
        self.assertTrue(packet["citation"].endswith("at [1(b)]"))
        self.assertEqual(packet["evidence"]["passages"][0]["text"], "A synthetic proposition.")

    def test_cite_check_requires_original_citation_record(self):
        self.as_cited()
        self.assertFalse(self.report()["errors"])
        del self.data["claims"][0]["citation_check"]
        self.assertTrue(any("preserving the original citation" in e for e in self.report()["errors"]))

    def test_corrected_pinpoint_cannot_replace_original_check(self):
        self.as_cited()
        ref = self.data["claims"][0]["evidence"][0]
        ref.update(pinpoint="[2]", passages=r.select_paragraphs(self.data["sources"][0]["paragraph_index"]["paragraphs"], "[2]"))
        self.assertTrue(any("checked separately from any correction" in e for e in self.report()["errors"]))

    def test_wrong_pinpoint_retains_original_and_separate_correction(self):
        self.as_cited(status="wrong-pinpoint")
        claim = self.data["claims"][0]
        claim["assessment"] = "qualified"
        correction = copy.deepcopy(claim["evidence"][0])
        correction.update(pinpoint="[2]", passages=r.select_paragraphs(self.data["sources"][0]["paragraph_index"]["paragraphs"], "[2]"),
                          support_note="Proposed replacement, separate from original [1].")
        claim["evidence"].append(correction)
        self.assertFalse(self.report()["errors"])
        claim["evidence"].pop()
        self.assertTrue(any("separately captured proposed replacement" in e for e in self.report()["errors"]))

    def test_original_citation_must_occur_in_draft(self):
        self.as_cited()
        self.data["claims"][0]["citation_check"]["citation"] = "Changed citation at [1]"
        self.assertTrue(any("not present in the inventoried draft" in e for e in self.report()["errors"]))

    def test_misattributed_original_pinpoint_is_rejected(self):
        self.as_cited()
        self.data["claims"][0]["citation_check"]["pinpoint"] = "[2]"
        self.assertTrue(any("does not occur in the original citation" in e for e in self.report()["errors"]))

    def test_equivalent_pinpoint_punctuation_keeps_original_text(self):
        self.as_cited(pin="[1] and [2]")
        ref = self.data["claims"][0]["evidence"][0]
        ref.update(pinpoint="[1], [2]", passages=r.select_paragraphs(self.data["sources"][0]["paragraph_index"]["paragraphs"], "[1], [2]"))
        self.assertFalse(self.report()["errors"])

    def test_unverified_pinpoint_cannot_be_marked_supported(self):
        self.as_cited(status="unverifiable")
        self.assertTrue(any("cannot be marked supported" in e for e in self.report()["errors"]))

    def test_page_fallback_must_be_explained_and_source_backed(self):
        source = self.case_source()
        del source["paragraph_index"]
        source["paragraphs_unavailable_reason"] = "Synthetic historical report has no numbered paragraphs."
        ref = self.data["claims"][0]["evidence"][0]
        ref.update(locator_type="page", pinpoint="p 10", locator_note="Compared passage to synthetic printed page 10.")
        ref["passages"] = [{k: v for k, v in ref["passages"][0].items() if k != "paragraph"}]
        self.assertFalse(self.report()["errors"])
        source["paragraphs_unavailable_reason"] = ""
        self.assertTrue(any("page fallback" in e for e in self.report()["errors"]))

    def test_draft_claim_must_be_linked_to_its_location(self):
        self.data["mode"] = "cite-check"
        self.data["inventory"] = [{"id": "manual/p:1", "text": "Synthetic draft passage.",
                                   "reviewed": True, "claim_ids": ["C1"], "reason": ""}]
        self.assertTrue(any("must identify this inventory location" in e for e in self.report()["errors"]))
        self.data["claims"][0]["location"] = "manual/p:1"
        self.assertFalse(self.report()["errors"])

    def test_orphan_cite_check_finding_cannot_pass(self):
        self.data["mode"] = "cite-check"
        self.data["inventory"] = [{"id": "manual/p:1", "text": "Synthetic draft passage.",
                                   "reviewed": True, "claim_ids": [], "reason": "Prose only."}]
        self.assertTrue(any("not linked to the draft inventory" in e for e in self.report()["errors"]))

    def test_export_library(self):
        self.data["sources"][0]["csl"] = {"type": "report", "title": "Synthetic test report"}
        self.save()
        target = self.base / "library.json"
        self.assertEqual(r.export_library(self.run, target)["exported"], 1)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))[0]["id"], "S1")
        with self.assertRaises(FileExistsError):
            r.export_library(self.run, target)

    def test_unreviewed_library_record_rejected(self):
        self.data["sources"][0].update(identity_verified=False,
            full_text_reviewed=False, csl={"type": "report", "title": "Synthetic"})
        self.data["claims"] = []
        self.data["mode"] = "library"
        self.save()
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            r.export_library(self.run, self.base / "library.json")

    def test_duplicate_library_record_rejected(self):
        s = self.data["sources"][0]
        s["csl"] = {"type": "report", "title": "Synthetic test report"}
        duplicate = copy.deepcopy(s)
        duplicate["id"] = "S2"
        self.data["sources"].append(duplicate)
        self.save()
        with self.assertRaisesRegex(ValueError, "duplicate legal identifier"):
            r.export_library(self.run, self.base / "library.json")


class QuoteTests(unittest.TestCase):
    TEXT = ("[1] The same synthetic words appear here.\n[2] Again the same synthetic words appear here.\n"
            "[3] Twice: the same synthetic words, and the same synthetic words.\n")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.run = self.base / "run"
        r.init_run(self.run, "Synthetic quote question", "research", "2026-10-20", "2026-10-20")
        source = self.base / "case.txt"
        source.write_text(self.TEXT, encoding="utf-8")
        r.snapshot(self.run, source, "S1", "Synthetic case — not law", "case",
                   "https://example.invalid/case", "SYNTHETIC-1", "synthetic version")
        r.index_paragraphs(self.run, "S1", "bracketed", "Synthetic boundaries reviewed.")

    def test_quote_binds_to_the_cited_paragraph_not_the_first_occurrence(self):
        quote = r.locate_quote(self.run, "S1", "[2]", "the same synthetic words", quote_id="Q1", claim_id="C1")
        self.assertEqual(quote["start"], self.TEXT.index("the same synthetic words", self.TEXT.index("[2]")))
        self.assertFalse(quote["pinpoint_reviewed"])
        self.assertNotIn("scope", quote)
        data = r.load_run(self.run)
        source = data["sources"][0]
        source.update(identity_verified=True, full_text_reviewed=True, publication_authority="Synthetic fixture only",
                      review_note="Reviewed.", retrieved_on="2026-10-20",
                      treatment={"status": "not-checked", "note": "Synthetic.", "search_ids": []})
        evidence = dict(r.capture_passages(self.run, "S1", "[2]")["evidence"], pinpoint_reviewed=True, support_note="Synthetic.")
        data.update(review="Synthetic review.", quotes=[dict(quote, pinpoint_reviewed=True)],
                    claims=[{"id": "C1", "text": "Synthetic.", "location": "answer/p:1", "assessment": "supported",
                             "reason": "Synthetic.", "evidence": [evidence]}])
        r.write_json(self.run / "run.json", data)
        self.assertFalse(r.check_run(self.run)["errors"])

    def test_subparagraph_quote_discloses_actual_search_scope(self):
        quote = r.locate_quote(self.run, "S1", "[1(b)]", "synthetic words")
        self.assertEqual(quote["pinpoint"], "[1(b)]")
        self.assertFalse(quote["pinpoint_reviewed"])
        self.assertEqual(quote["scope"]["kind"], "full-numbered-paragraphs")
        self.assertEqual(quote["scope"]["searched_paragraphs"], [1])
        self.assertIn("sibling text may match", quote["scope"]["warning"])

    def test_cli_subparagraph_range_reports_all_parent_paragraphs(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, "-I", str(SCRIPT), "quote", str(self.run),
                                 "--source", "S1", "--pinpoint", "[1(a)]-[2(b)]", "--text", "Again the same"],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        quote = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(quote["scope"]["searched_paragraphs"], [1, 2])
        self.assertEqual(quote["scope"]["requested_pinpoint"], "[1(a)]–[2(b)]")
        self.assertIn("Manually verify", quote["scope"]["warning"])

    def test_words_outside_the_cited_paragraph_are_located_for_the_reviewer(self):
        with self.assertRaisesRegex(ValueError, r"not found in \[1\]; the words occur at \[2\]"):
            r.locate_quote(self.run, "S1", "[1]", "Again the same")
        with self.assertRaisesRegex(ValueError, "do not occur in the source"):
            r.locate_quote(self.run, "S1", "[1]", "Invented synthetic words")

    def test_repeated_words_need_an_occurrence(self):
        with self.assertRaisesRegex(ValueError, "occur 2 times"):
            r.locate_quote(self.run, "S1", "[3]", "the same synthetic words")
        second = r.locate_quote(self.run, "S1", "[3]", "the same synthetic words", occurrence=2)
        self.assertEqual(second["start"], self.TEXT.rindex("the same synthetic words"))

    def test_whitespace_differences_match_but_ellipses_are_refused(self):
        quote = r.locate_quote(self.run, "S1", "at [2]", "Again  the\nsame synthetic")
        self.assertEqual(quote["text"], "Again the same synthetic")
        with self.assertRaisesRegex(ValueError, "ellipsis"):
            r.locate_quote(self.run, "S1", "[2]", "Again … words")


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.file = self.base / "draft.docx"
        make_docx(self.file)

    def test_body_table_footnotes_endnotes_and_note_ids(self):
        x = r.extract_docx(self.file)
        self.assertEqual(len(x["blocks"]), 4)
        self.assertIn("[footnote-id:7]", x["blocks"][0]["text"])
        self.assertTrue(any(b["id"] == "footnote-id:7/p:1" for b in x["blocks"]))
        self.assertTrue(any(b["text"] == "Table authority." for b in x["blocks"]))
        self.assertFalse(any("Do not inventory" in b["text"] for b in x["blocks"]))

    def test_tracked_changes_and_fields_are_flagged(self):
        make_docx(self.file, '<w:p><w:del><w:r><w:delText>Deleted.</w:delText></w:r></w:del>'
                  '<w:ins><w:r><w:t>Inserted.</w:t></w:r></w:ins>'
                  '<w:r><w:fldChar w:fldCharType="begin"/></w:r></w:p>')
        x = r.extract_docx(self.file)
        self.assertTrue(any("tracked changes" in w for w in x["warnings"]))
        self.assertTrue(any("fields present" in w for w in x["warnings"]))
        self.assertIn("Deleted.", x["blocks"][0]["text"])

    def test_missing_inventory_block_cannot_pass(self):
        run = self.base / "run"
        r.init_run(run, "Check synthetic draft", "cite-check", "2026-10-20", "2026-10-20")
        r.attach_draft(run, self.file)
        data = r.load_run(run)
        data["review"] = "Synthetic review"
        for b in data["inventory"]:
            b.update(reviewed=True, reason="Synthetic prose only.")
        r.write_json(run / "run.json", data)
        self.assertEqual(r.check_run(run)["status"], "pass-with-limits")
        data["inventory"].pop()
        r.write_json(run / "run.json", data)
        self.assertTrue(any("exact draft blocks" in e for e in r.check_run(run)["errors"]))

    def test_draft_snapshot_is_immutable(self):
        run = self.base / "run"
        r.init_run(run, "Check synthetic draft", "cite-check", "2026-10-20", "2026-10-20")
        r.attach_draft(run, self.file)
        with self.assertRaisesRegex(ValueError, "already attached"):
            r.attach_draft(run, self.file)


if __name__ == "__main__":
    unittest.main()
