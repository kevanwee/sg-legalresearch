"""Synthetic written-law fixtures only; no real duties or instruments are asserted."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/singapore-legal-research/scripts/research.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("statutory_research", SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

TEXT = ("9A.—(1) A synthetic definition.\n"
        "(2) A synthetic duty applies if:\n"
        "(a) the first condition is met;\n"
        "(b) the second condition is met.\n"
        "9B.—A separate synthetic duty.\n"
        "ORDER 9\n1.—(1) A synthetic procedural rule.\n"
        "FIRST SCHEDULE\n2. A synthetic schedule item.\n")


def provision_map(data, source):
    specs = [("s 9A", "9A.", "9B."), ("s 9A(1)", "(1) A synthetic definition", "(2)"),
             ("s 9A(2)", "(2)", "9B."), ("s 9A(2)(a)", "(a)", "(b)"),
             ("s 9A(2)(b)", "(b)", "9B."), ("s 9B", "9B.", "ORDER"),
             ("O 9", "ORDER", "FIRST"), ("O 9 r 1", "1.—", "FIRST"),
             ("O 9 r 1(1)", "(1) A synthetic procedural", "FIRST"),
             ("First Schedule", "FIRST", None), ("First Schedule para 2", "2. A synthetic", None)]
    rows = []
    for locator, first, last in specs:
        start = TEXT.index(first)
        end = TEXT.index(last, start + len(first)) if last else len(TEXT)
        rows.append({"locator": locator, "start": start, "end": end, "status": "in-force",
                     "status_note": "Synthetic fixture's operative status reviewed; not actual law."})
    return {"provisions": rows, "statute_verification": {
        "run_id": data["run_id"], "draft_sha256": data["draft"]["sha256"] if data["draft"] else None,
        "instrument_title": source["title"], "instrument_citation": source["citation"], "instrument_kind": "act",
        "source_version": source["version"],
        "law_as_at": data["law_as_at"], "checked_on": data["research_date"],
        "identity_note": "Matched synthetic title, year and identifier, not a similarly named fixture.",
        "version_note": "Selected the fixture version for the synthetic event date.",
        "commencement_note": "Synthetic provision-level status, amendments and savings checked."}}


class StatutoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.run = self.base / "run"
        r.init_run(self.run, "Synthetic statute research", "research", "2026-10-20", "2026-10-20")
        source_file = self.base / "source.txt"
        source_file.write_text(TEXT, encoding="utf-8")
        r.snapshot(self.run, source_file, "L1", "Synthetic Act 2000", "legislation",
                   "https://example.invalid/act", "SYNTHETIC-ACT-1", "synthetic 2026 version")
        data = r.load_run(self.run)
        self.manifest = provision_map(data, data["sources"][0])
        r.index_provisions(self.run, "L1", self.manifest, "Synthetic labels, complete units and parent scope reviewed.")
        packet = r.capture_provision(self.run, "L1", "s 9A(2)(a)")
        self.data = r.load_run(self.run)
        self.data["review"] = "Synthetic same-agent test review."
        self.data["sources"][0].update(identity_verified=True, full_text_reviewed=True,
            publication_authority="Synthetic fixture only", retrieved_on="2026-10-20", review_note="Read fixture.",
            version_review="Synthetic operative section and later changes checked.")
        packet["evidence"].update(pinpoint_reviewed=True, support_note="Synthetic condition (a).")
        self.data["claims"] = [{"id": "C1", "text": "The synthetic condition applies.", "location": "answer/p:1",
            "assessment": "supported", "reason": "Synthetic support review.", "evidence": [packet["evidence"]]}]

    def report(self):
        r.write_json(self.run / "run.json", self.data)
        return r.check_run(self.run)

    def cited(self):
        self.data["mode"] = "cite-check"
        citation = "Synthetic Act 2000 s 9A(2)(a)"
        self.data["claims"][0].update(location="draft/p:1", citation_check={
            "source_id": "L1", "citation": citation, "pinpoint": "s 9A(2)(a)", "result": "supported",
            "reason": "Synthetic cited provision supports the draft.", "resolved_instrument": "Synthetic Act 2000",
            "instrument_result": "matched", "instrument_note": "Matched the precise synthetic instrument.",
            "version_result": "matched", "version_note": "Matched the synthetic operative text.",
            "applicable_on": "2026-10-20", "date_basis": "Synthetic relevant event occurred on this date."})
        self.data["inventory"] = [{"id": "draft/p:1", "text": "Proposition: " + citation + ".",
                                   "reviewed": True, "claim_ids": ["C1"], "reason": ""}]

    def test_exact_subsection_and_all_parent_context(self):
        self.assertFalse(self.report()["errors"])
        ref = self.data["claims"][0]["evidence"][0]
        self.assertEqual([p["locator"] for p in ref["context"]], ["s 9A", "s 9A(2)"])
        self.assertEqual(ref["passages"][0]["text"], "(a) the first condition is met;\n")

    def test_statutory_paraphrase_needs_captured_provision(self):
        del self.data["claims"][0]["evidence"][0]["passages"]
        self.assertTrue(any("exact cited provision" in e for e in self.report()["errors"]))

    def test_quote_elsewhere_in_act_does_not_verify_section(self):
        words = "A separate synthetic duty."
        start = TEXT.index(words)
        self.data["quotes"] = [{"id": "Q1", "claim_id": "C1", "source_id": "L1", "pinpoint": "s 9A(2)(a)",
                                "text": words, "start": start, "end": start + len(words), "pinpoint_reviewed": True}]
        self.assertTrue(any("outside the full paragraphs/passages" in e for e in self.report()["errors"]))

    def test_quote_from_the_exact_cited_subsection_passes(self):
        words = "the first condition is met;"
        start = TEXT.index(words)
        self.data["quotes"] = [{"id": "Q1", "claim_id": "C1", "source_id": "L1", "pinpoint": "s 9A(2)(a)",
                                "text": words, "start": start, "end": start + len(words), "pinpoint_reviewed": True}]
        self.assertFalse(self.report()["errors"])

    def test_parent_context_does_not_verify_uncited_sibling(self):
        words = "the second condition is met."
        start = TEXT.index(words)
        self.data["quotes"] = [{"id": "Q1", "claim_id": "C1", "source_id": "L1", "pinpoint": "s 9A(2)(a)",
                                "text": words, "start": start, "end": start + len(words), "pinpoint_reviewed": True}]
        self.assertTrue(any("outside the full paragraphs/passages" in e for e in self.report()["errors"]))

    def test_wrong_leaf_cannot_be_relabelled(self):
        ref = self.data["claims"][0]["evidence"][0]
        ref["passages"][0]["text"] = "(b) the second condition is met."
        self.assertTrue(any("exact cited provision" in e for e in self.report()["errors"]))

    def test_wrong_source_label_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["provisions"][3]["locator"] = "s 9A(2)(c)"
        with self.assertRaisesRegex(ValueError, "correct provision label"):
            r.build_provisions(TEXT, manifest)

    def test_child_must_belong_to_its_actual_parent(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["provisions"][0]["end"] = TEXT.index("(2)")
        with self.assertRaisesRegex(ValueError, "complete parent"):
            r.build_provisions(TEXT, manifest)

    def test_changed_provision_index_is_rejected(self):
        self.data["sources"][0]["provision_index"]["provisions"][0]["text"] = "Altered text"
        self.assertTrue(any("does not match source labels" in e for e in self.report()["errors"]))

    def test_receipt_cannot_be_reused_from_another_run(self):
        self.data["sources"][0]["statute_verification"]["run_id"] = "old-run"
        self.assertTrue(any("rechecked for this run" in e for e in self.report()["errors"]))

    def test_receipt_must_be_rechecked_on_research_date(self):
        self.data["sources"][0]["statute_verification"]["checked_on"] = "2025-10-20"
        self.assertTrue(any("research date" in e for e in self.report()["errors"]))

    def test_receipt_must_match_the_precise_draft(self):
        self.data["sources"][0]["statute_verification"]["draft_sha256"] = "different-draft"
        self.assertTrue(any("different draft snapshot" in e for e in self.report()["errors"]))

    def test_instrument_receipt_matches_actual_source(self):
        self.data["sources"][0]["statute_verification"]["instrument_title"] = "Similarly Named Regulations 2000"
        self.assertTrue(any("actual source instrument" in e for e in self.report()["errors"]))

    def test_source_version_label_cannot_change_without_reverification(self):
        self.data["sources"][0]["version"] = "a different synthetic edition/version"
        self.assertTrue(any("actual source version" in e for e in self.report()["errors"]))

    def test_cite_check_requires_instrument_and_version_findings(self):
        self.cited()
        self.assertFalse(self.report()["errors"])
        del self.data["claims"][0]["citation_check"]["instrument_result"]
        del self.data["claims"][0]["citation_check"]["version_result"]
        errors = self.report()["errors"]
        self.assertTrue(any("instrument_result" in e for e in errors))
        self.assertTrue(any("version_result" in e for e in errors))

    def test_wrong_statute_cannot_be_marked_supported(self):
        self.cited()
        self.data["claims"][0]["citation_check"]["instrument_result"] = "wrong-instrument"
        self.assertTrue(any("wrong or unverified instrument/version" in e for e in self.report()["errors"]))

    def test_wrong_version_is_a_separate_visible_finding(self):
        self.cited()
        claim = self.data["claims"][0]
        claim.update(assessment="qualified")
        claim["citation_check"].update(result="wrong-version", version_result="wrong-version",
                                      version_note="The draft selects the wrong synthetic version.")
        report = self.report()
        self.assertFalse(report["errors"])
        self.assertTrue(any("wrong-version" in limit for limit in report["limits"]))

    def test_wrong_instrument_is_a_separate_visible_finding(self):
        self.cited()
        claim = self.data["claims"][0]
        claim["assessment"] = "unsupported"
        claim["citation_check"].update(result="wrong-instrument", instrument_result="wrong-instrument",
                                        instrument_note="The draft cites a different synthetic instrument from the one needed.")
        report = self.report()
        self.assertFalse(report["errors"])
        self.assertTrue(any("wrong-instrument" in limit for limit in report["limits"]))

    def test_corrected_section_cannot_silently_replace_original(self):
        self.cited()
        rows = self.data["sources"][0]["provision_index"]["provisions"]
        ref = self.data["claims"][0]["evidence"][0]
        passages, context = r.select_provision(rows, "s 9A(2)(b)")
        ref.update(pinpoint="s 9A(2)(b)", passages=passages, context=context)
        self.assertTrue(any("checked separately from any correction" in e for e in self.report()["errors"]))

    def test_wrong_section_keeps_original_and_proposed_correction(self):
        self.cited()
        claim = self.data["claims"][0]
        claim["assessment"] = "qualified"
        claim["citation_check"].update(result="wrong-pinpoint", reason="Synthetic original and replacement provision compared.")
        correction = copy.deepcopy(claim["evidence"][0])
        passages, context = r.select_provision(self.data["sources"][0]["provision_index"]["provisions"], "s 9A(2)(b)")
        correction.update(pinpoint="s 9A(2)(b)", passages=passages, context=context)
        claim["evidence"].append(correction)
        self.assertFalse(self.report()["errors"])

    def test_historical_comparison_needs_a_date_basis(self):
        source = self.data["sources"][0]
        source["statute_verification"]["law_as_at"] = "2020-01-01"
        ref = self.data["claims"][0]["evidence"][0]
        ref["law_as_at"] = "2020-01-01"
        self.assertTrue(any("historical comparison" in e for e in self.report()["errors"]))
        ref["date_basis"] = "Comparing the historical version expressly cited in the draft."
        self.assertFalse(self.report()["errors"])

    def test_correct_title_but_wrong_applicable_date_fails(self):
        self.cited()
        self.data["claims"][0]["citation_check"]["applicable_on"] = "2020-01-01"
        self.assertTrue(any("verified for its applicable date" in e for e in self.report()["errors"]))

    def test_ref_version_date_must_match_source(self):
        self.data["claims"][0]["evidence"][0]["law_as_at"] = "2020-01-01"
        self.assertTrue(any("does not match the verified source version" in e for e in self.report()["errors"]))

    def test_rule_and_schedule_retain_hierarchy(self):
        rows = self.data["sources"][0]["provision_index"]["provisions"]
        selected, context = r.select_provision(rows, "Order 9 rule 1(1)")
        self.assertEqual(selected[0]["locator"], "O 9 r 1(1)")
        self.assertEqual([p["locator"] for p in context], ["O 9", "O 9 r 1"])
        selected, context = r.select_provision(rows, "First Schedule, paragraph 2")
        self.assertEqual(selected[0]["locator"], "First Schedule para 2")
        self.assertEqual(context[0]["locator"], "First Schedule")

    def test_pending_provision_is_disclosed(self):
        source = self.data["sources"][0]
        row = next(p for p in source["provision_index"]["provisions"] if p["locator"] == "s 9A(2)(a)")
        row.update(status="not-in-force", status_note="Synthetic deferred commencement.")
        self.data["claims"][0]["evidence"][0]["passages"] = [copy.deepcopy(row)]
        self.assertTrue(any("not-in-force" in limit for limit in self.report()["limits"]))

    def test_missing_or_unsupported_locator_is_not_guessed(self):
        rows = self.data["sources"][0]["provision_index"]["provisions"]
        for pin in ("s 999", "s 9A(3)", "ss 9A-9B", "9A"):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                r.select_provision(rows, pin)

    def test_standalone_statutory_cli(self):
        map_file = self.base / "map.json"
        r.write_json(map_file, self.manifest, new=True)
        args = [sys.executable, str(SCRIPT), "index-provisions", str(self.run), "--source", "L1",
                "--map", str(map_file), "--confirm-boundaries", "--review-note", "Synthetic source boundaries checked."]
        result = subprocess.run(args, capture_output=True, text=True, cwd=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = subprocess.run([sys.executable, str(SCRIPT), "provision", str(self.run), "--source", "L1",
                                 "--locator", "s 9A(2)(a)"], capture_output=True, text=True, cwd=self.base)
        self.assertEqual(packet.returncode, 0, packet.stderr)
        self.assertFalse(json.loads(packet.stdout)["evidence"]["pinpoint_reviewed"])


if __name__ == "__main__":
    unittest.main()
