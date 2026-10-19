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
        s = self.data["sources"][0]
        s.update(kind="case", treatment={"status": "public-search-limited",
            "note": "Synthetic searches only; no citator.", "search_ids": ["T1"]})
        self.data["search_log"] = [{"id": "T1", "database": "Synthetic database",
            "query": "SYNTHETIC-1", "coverage": "Synthetic fixture only", "result_note": "No matches in fixture.",
            "searched_on": "2026-10-20"}]
        self.assertEqual(self.report()["status"], "pass-with-limits")

    def test_treatment_claim_needs_search_evidence(self):
        self.data["sources"][0].update(kind="case", treatment={"status": "citator-checked",
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
