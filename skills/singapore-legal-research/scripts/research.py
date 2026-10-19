#!/usr/bin/env python3
"""Offline evidence helpers. No legal database API, citator, or semantic verifier."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

MODES = ("research", "deep-research", "find-authority", "cite-check",
         "legislation-hansard", "case-prep", "library", "proofread")
KINDS = ("case", "legislation", "hansard", "bill", "secondary", "other")
ASSESSMENTS = ("supported", "qualified", "unsupported", "unresolved", "editorial")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def normalise(text):
    # Whitespace and Unicode composition only: no case/punctuation/word changes.
    return " ".join(unicodedata.normalize("NFC", text).split())


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("date must use YYYY-MM-DD")
    date.fromisoformat(value)
    return value


def inside(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("evidence paths must be non-empty relative paths")
    target = (Path(root) / relative).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise ValueError("evidence path escapes the run folder")
    return target


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value, *, new=False):
    path = Path(path)
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if new:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    else:
        temporary = path.with_name(path.name + ".tmp")
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        temporary.replace(path)


def load_run(root):
    data = read_json(Path(root) / "run.json")
    if not isinstance(data, dict):
        raise ValueError("run.json must be an object")
    return data


def init_run(root, question, mode, research_date, law_as_at):
    iso_date(research_date)
    iso_date(law_as_at)
    if mode not in MODES or not nonempty(question):
        raise ValueError("a question and a supported mode are required")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 1, "question": question, "mode": mode,
            "research_date": research_date, "law_as_at": law_as_at,
            "sources": [], "claims": [], "quotes": [], "inventory": [],
            "search_log": [], "gaps": [], "review": "", "draft": None}
    write_json(root / "run.json", data, new=True)
    return data


def snapshot(root, file, source_id, title, kind, url, citation, version,
             text_file=None, transformation=""):
    root = Path(root)
    data = load_run(root)
    if not ID.fullmatch(source_id) or kind not in KINDS:
        raise ValueError("invalid source id or kind")
    if any(s.get("id") == source_id for s in data["sources"]):
        raise ValueError("source id already exists")
    if not all(nonempty(v) for v in (title, url, citation, version)):
        raise ValueError("title, URL, citation, and actual version are required")
    if text_file and not nonempty(transformation):
        raise ValueError("a derived text file needs a transformation description")
    file = Path(file)
    if not text_file:
        file.read_text(encoding="utf-8-sig")  # Reject binary input as quotation text.
    else:
        Path(text_file).read_text(encoding="utf-8-sig")
    folder = root / "sources" / source_id
    folder.mkdir(parents=True, exist_ok=False)
    original = folder / ("source" + file.suffix.lower())
    shutil.copyfile(file, original)
    text_path = original
    if text_file:
        text_path = folder / "extracted.txt"
        shutil.copyfile(text_file, text_path)
    source = {"id": source_id, "title": title, "kind": kind, "url": url,
              "citation": citation, "version": version,
              "snapshotted_at": datetime.now(timezone.utc).isoformat(),
              "retrieved_on": "", "file": original.relative_to(root).as_posix(),
              "sha256": digest(original), "text_file": text_path.relative_to(root).as_posix(),
              "text_sha256": digest(text_path), "transformation": transformation,
              "publication_authority": "", "identity_verified": False,
              "full_text_reviewed": False, "review_note": "", "version_review": "",
              "treatment": {"status": "not-checked", "note": "", "search_ids": []}}
    data["sources"].append(source)
    write_json(root / "run.json", data)
    return source


def xml_text(node):
    pieces = []
    for child in node.iter():
        if child.tag in (W + "t", W + "delText"):
            pieces.append(child.text or "")
        elif child.tag == W + "tab":
            pieces.append("\t")
        elif child.tag in (W + "br", W + "cr"):
            pieces.append("\n")
        elif child.tag in (W + "footnoteReference", W + "endnoteReference"):
            label = child.tag.split("}")[1].replace("Reference", "")
            pieces.append(f"[{label}-id:{child.get(W + 'id')}]")
    return "".join(pieces)


def extract_docx(file):
    """Inventory paragraphs including table cells; retain note IDs and warn on revisions."""
    blocks, warnings = [], []
    with zipfile.ZipFile(file) as archive:
        if sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError("DOCX uncompressed content exceeds 100 MiB")
        for part in ("document", "footnotes", "endnotes"):
            name = f"word/{part}.xml"
            if name not in archive.namelist():
                if part == "document":
                    raise ValueError("missing Word document body")
                continue
            xml = ET.fromstring(archive.read(name))
            if any(n.tag in (W + "ins", W + "del", W + "moveFrom", W + "moveTo") for n in xml.iter()):
                warnings.append(f"{part}: tracked changes present; extracted text is not an accepted/final view")
            if any(n.tag in (W + "fldChar", W + "instrText", W + "fldSimple") for n in xml.iter()):
                warnings.append(f"{part}: fields present; verify displayed values and citation fields in Word")
            if part == "document":
                groups = [("body", xml)]
            else:
                singular = part[:-1]
                groups = [(f"{singular}-id:{n.get(W + 'id')}", n)
                          for n in xml.findall(W + singular)
                          if n.get(W + "type", "normal") == "normal"]
            for prefix, group in groups:
                for number, para in enumerate(group.iter(W + "p"), 1):
                    text = xml_text(para)
                    if text.strip():
                        blocks.append({"id": f"{prefix}/p:{number}", "text": text})
        if any(n.startswith(("word/header", "word/footer", "word/comments")) for n in archive.namelist()):
            warnings.append("Headers, footers and comments are not inventoried; inspect separately if in scope")
    warnings.append("OOXML note IDs may differ from displayed numbers; reconcile with Word. Text boxes and complex layouts need visual review.")
    return {"blocks": blocks, "warnings": warnings}


def attach_draft(root, file):
    root = Path(root)
    data = load_run(root)
    if data.get("draft") or data.get("inventory"):
        raise ValueError("draft already attached; use a new run for a revised draft")
    extracted = extract_docx(file)
    if not extracted["blocks"]:
        raise ValueError("draft contains no extractable text")
    folder = root / "draft"
    folder.mkdir(exist_ok=False)
    target = folder / "snapshot.docx"
    shutil.copyfile(file, target)
    write_json(folder / "extraction.json", extracted, new=True)
    data["draft"] = {"file": "draft/snapshot.docx", "sha256": digest(target),
                     "extraction": "draft/extraction.json", "extraction_sha256": digest(folder / "extraction.json")}
    data["inventory"] = [dict(b, reviewed=False, claim_ids=[], reason="") for b in extracted["blocks"]]
    data["gaps"].extend(extracted["warnings"])
    write_json(root / "run.json", data)
    return extracted


def check_run(root):
    root = Path(root)
    data = load_run(root)
    errors, limits = [], []
    if data.get("schema_version") != 1:
        errors.append("unsupported schema_version")
    for field in ("question", "review"):
        if not nonempty(data.get(field)):
            errors.append(f"missing {field}")
    if data.get("mode") not in MODES:
        errors.append("invalid mode")
    for field in ("research_date", "law_as_at"):
        try:
            iso_date(data.get(field))
        except ValueError:
            errors.append(f"invalid {field}")
    for field in ("sources", "claims", "quotes", "inventory", "search_log", "gaps"):
        if not isinstance(data.get(field), list):
            errors.append(f"{field} must be an array")
    if errors:
        return result(data, errors, limits)

    def indexed(items, label):
        output = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                errors.append(f"{label}: every record needs an id")
            elif item["id"] in output:
                errors.append(f"{label}: duplicate id {item['id']}")
            else:
                output[item["id"]] = item
        return output

    sources = indexed(data["sources"], "sources")
    claims = indexed(data["claims"], "claims")
    searches = indexed(data["search_log"], "search_log")
    inventory = indexed(data["inventory"], "inventory")
    quotes = indexed(data["quotes"], "quotes")
    texts = {}

    def check_hash(record, path_key, hash_key, label):
        try:
            path = inside(root, record.get(path_key))
            if digest(path) != record.get(hash_key):
                raise ValueError("hash mismatch")
            return path
        except (OSError, ValueError) as exc:
            errors.append(f"{label}: {path_key}: {exc}")
            return None

    for key, search in searches.items():
        if not all(nonempty(search.get(f)) for f in ("database", "query", "coverage", "result_note")):
            errors.append(f"{key}: incomplete search record")
        try:
            iso_date(search.get("searched_on"))
        except ValueError:
            errors.append(f"{key}: invalid searched_on")
    for key, source in sources.items():
        if not ID.fullmatch(key) or source.get("kind") not in KINDS:
            errors.append(f"{key}: invalid source id or kind")
        for f in ("title", "url", "citation", "version"):
            if not nonempty(source.get(f)):
                errors.append(f"{key}: missing {f}")
        for f in ("identity_verified", "full_text_reviewed"):
            if not isinstance(source.get(f), bool):
                errors.append(f"{key}: {f} must be boolean")
        check_hash(source, "file", "sha256", key)
        path = check_hash(source, "text_file", "text_sha256", key)
        if source.get("text_file") != source.get("file") and not nonempty(source.get("transformation")):
            errors.append(f"{key}: missing transformation description")
        if path:
            try:
                texts[key] = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{key}: cannot read UTF-8 source text: {exc}")
        if source.get("identity_verified") is True or source.get("full_text_reviewed") is True:
            for f in ("publication_authority", "review_note"):
                if not nonempty(source.get(f)):
                    errors.append(f"{key}: reviewed source missing {f}")
            try:
                iso_date(source.get("retrieved_on"))
            except ValueError:
                errors.append(f"{key}: reviewed source needs retrieved_on")
        if not (source.get("identity_verified") is True and source.get("full_text_reviewed") is True):
            limits.append(f"{key}: source not reviewed")

    used = set()
    for key, claim in claims.items():
        assessment = claim.get("assessment")
        if assessment not in ASSESSMENTS or not all(nonempty(claim.get(f)) for f in ("text", "location", "reason")):
            errors.append(f"{key}: incomplete claim or invalid assessment")
        refs = claim.get("evidence")
        if not isinstance(refs, list):
            errors.append(f"{key}: evidence must be an array")
            continue
        if assessment in ("supported", "qualified") and not refs:
            errors.append(f"{key}: support requires evidence")
        if assessment in ("qualified", "unsupported", "unresolved"):
            limits.append(f"{key}: {assessment}: {claim.get('reason', '')}")
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append(f"{key}: malformed evidence reference")
                continue
            sid = ref.get("source_id")
            if not isinstance(sid, str) or sid not in sources:
                errors.append(f"{key}: unknown source_id")
                continue
            used.add(sid)
            if not all(nonempty(ref.get(f)) for f in ("pinpoint", "support_note")) or ref.get("pinpoint_reviewed") is not True:
                errors.append(f"{key}: evidence needs pinpoint, support_note and pinpoint_reviewed=true")
            if assessment in ("supported", "qualified") and not (
                    sources[sid].get("identity_verified") is True and sources[sid].get("full_text_reviewed") is True):
                errors.append(f"{key}: support relies on unreviewed source {sid}")

    for sid in used:
        source = sources[sid]
        if source.get("kind") == "legislation" and not nonempty(source.get("version_review")):
            errors.append(f"{sid}: legislation needs provision-specific version_review")
        if source.get("kind") == "case":
            treatment = source.get("treatment", {})
            if not isinstance(treatment, dict) or treatment.get("status") not in (
                    "not-checked", "public-search-limited", "citator-checked", "adverse-treatment-found"):
                errors.append(f"{sid}: invalid treatment record")
                continue
            if not nonempty(treatment.get("note")):
                errors.append(f"{sid}: case needs a treatment note")
            ids = treatment.get("search_ids")
            if not isinstance(ids, list) or any(not isinstance(i, str) or i not in searches for i in ids):
                errors.append(f"{sid}: invalid treatment search_ids")
            elif treatment["status"] != "not-checked" and not ids:
                errors.append(f"{sid}: treatment check needs search records")
            if treatment["status"] != "citator-checked":
                limits.append(f"{sid}: treatment {treatment['status']}: {treatment.get('note', '')}")

    for key, quote in quotes.items():
        sid, cid = quote.get("source_id"), quote.get("claim_id")
        if not isinstance(sid, str) or sid not in texts or not isinstance(cid, str) or cid not in claims:
            errors.append(f"{key}: unknown quote source or claim")
            continue
        refs = claims[cid].get("evidence", [])
        if not isinstance(refs, list) or not any(isinstance(r, dict) and r.get("source_id") == sid and r.get("pinpoint") == quote.get("pinpoint") for r in refs):
            errors.append(f"{key}: quote source and pinpoint must be linked to its claim")
        start, end = quote.get("start"), quote.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(texts[sid]):
            errors.append(f"{key}: invalid character span")
        elif not nonempty(quote.get("text")) or normalise(texts[sid][start:end]) != normalise(quote["text"]):
            errors.append(f"{key}: quotation does not match the recorded source span")
        if quote.get("pinpoint_reviewed") is not True or not nonempty(quote.get("pinpoint")):
            errors.append(f"{key}: quote pinpoint not reviewed")
        if not (sources[sid].get("identity_verified") is True and sources[sid].get("full_text_reviewed") is True):
            errors.append(f"{key}: quotation source is unreviewed")

    draft = data.get("draft")
    if data["mode"] == "cite-check" and not draft and not inventory:
        errors.append("cite-check needs a draft inventory")
    if draft is not None:
        if not isinstance(draft, dict):
            errors.append("draft must be an object or null")
        else:
            path = check_hash(draft, "file", "sha256", "draft")
            extraction_path = check_hash(draft, "extraction", "extraction_sha256", "draft")
            if path and extraction_path:
                try:
                    original = extract_docx(path)
                    saved = read_json(extraction_path)
                    if saved != original:
                        errors.append("draft extraction differs from the snapshot")
                    expected = {b["id"]: b["text"] for b in original["blocks"]}
                    actual = {k: v.get("text") for k, v in inventory.items()}
                    if expected != actual:
                        errors.append("inventory does not cover the exact draft blocks")
                except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
                    errors.append(f"draft extraction cannot be verified: {exc}")
    for key, item in inventory.items():
        ids = item.get("claim_ids")
        if not nonempty(item.get("text")):
            errors.append(f"{key}: inventory needs the exact draft text")
        if item.get("reviewed") is not True:
            errors.append(f"{key}: inventory location not reviewed")
        if not isinstance(ids, list) or any(not isinstance(i, str) or i not in claims for i in ids):
            errors.append(f"{key}: invalid claim_ids")
        elif not ids and not nonempty(item.get("reason")):
            errors.append(f"{key}: explain why there are no research items")
        elif ids:
            for cid in ids:
                if claims[cid].get("location") != key:
                    errors.append(f"{key}: claim {cid} must identify this inventory location")
    if data["mode"] == "cite-check":
        linked = {cid for item in inventory.values() for cid in item.get("claim_ids", [])
                  if isinstance(cid, str)} if all(isinstance(i.get("claim_ids"), list) for i in inventory.values()) else set()
        for cid in claims:
            if cid not in linked:
                errors.append(f"{cid}: cite-check finding is not linked to the draft inventory")
    if not claims and data["mode"] not in ("library", "proofread", "cite-check"):
        errors.append("research run has no claims")
    if data["mode"] == "library" and not sources:
        errors.append("library run has no sources")
    for gap in data["gaps"]:
        if not nonempty(gap):
            errors.append("gaps must contain non-empty descriptions")
        else:
            limits.append(gap)
    return result(data, errors, limits)


def result(data, errors, limits):
    return {"status": "fail" if errors else ("pass-with-limits" if limits else "pass-record-checks"),
            "errors": errors, "limits": limits,
            "counts": {k: len(data[k]) for k in ("sources", "claims", "quotes", "inventory", "search_log")
                       if isinstance(data.get(k), list)},
            "meaning": "Record integrity and declared review only; not legal correctness, authenticity, completeness, or current-law certification."}


def export_library(root, output):
    report = check_run(root)
    if report["errors"]:
        raise ValueError("run record checks failed; run check for details")
    data, records, seen = load_run(root), [], set()
    for source in data["sources"]:
        if "csl" not in source:
            continue
        if source.get("identity_verified") is not True or source.get("full_text_reviewed") is not True:
            raise ValueError(f"{source['id']}: cannot export an unreviewed record")
        record = source["csl"]
        if not isinstance(record, dict) or not all(nonempty(record.get(f)) for f in ("type", "title")):
            raise ValueError("CSL record needs a verified type and title")
        if record["type"] not in ("legal_case", "legislation", "article-journal", "book", "report", "webpage", "speech", "chapter"):
            raise ValueError("unsupported CSL type; extend deliberately if needed")
        key = (normalise(source["citation"]).casefold(), normalise(source["version"]).casefold())
        if key in seen:
            raise ValueError("duplicate legal identifier and version in library export")
        seen.add(key)
        record = dict(record, id=source["id"], URL=source["url"])
        records.append(record)
    if not records:
        raise ValueError("no reviewed sources with CSL metadata to export")
    write_json(output, records, new=True)
    return {"exported": len(records), "path": str(output), "limits": report["limits"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create a new private research ledger")
    init.add_argument("run", type=Path)
    init.add_argument("--question", required=True)
    init.add_argument("--mode", choices=MODES, default="research")
    init.add_argument("--research-date", type=iso_date, required=True)
    init.add_argument("--law-as-at", type=iso_date, required=True)
    snap = sub.add_parser("snapshot", help="copy a retrieved source and record its hashes")
    snap.add_argument("run", type=Path)
    snap.add_argument("file", type=Path)
    for arg in ("id", "title", "url", "citation", "version"):
        snap.add_argument("--" + arg, required=True)
    snap.add_argument("--kind", choices=KINDS, required=True)
    snap.add_argument("--text", type=Path)
    snap.add_argument("--transformation", default="")
    docx = sub.add_parser("extract-docx", help="snapshot a Word draft and inventory text")
    docx.add_argument("run", type=Path)
    docx.add_argument("file", type=Path)
    check = sub.add_parser("check", help="check records, snapshots, coverage and quotation spans")
    check.add_argument("run", type=Path)
    export = sub.add_parser("export-library", help="write reviewed source records to CSL-JSON")
    export.add_argument("run", type=Path)
    export.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            init_run(args.run, args.question, args.mode, args.research_date, args.law_as_at)
            output = {"created": str(args.run / "run.json")}
        elif args.command == "snapshot":
            output = snapshot(args.run, args.file, args.id, args.title, args.kind, args.url,
                              args.citation, args.version, args.text, args.transformation)
        elif args.command == "extract-docx":
            output = attach_draft(args.run, args.file)
        elif args.command == "check":
            output = check_run(args.run)
        else:
            output = export_library(args.run, args.output)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 1 if output.get("status") == "fail" else 0
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
