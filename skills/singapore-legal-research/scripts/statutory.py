"""Source-span indexes for legislation. Boundaries and legal effect require review."""

import re
from datetime import date


def provision_locator(value):
    """Return a canonical locator, immediate parent and source-label pattern."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("a specific statutory provision is required")
    value = re.sub(r"\s+", " ", value.strip())
    tail = r"((?:\([A-Za-z0-9]+\))*)"
    number = r"([1-9]\d*[A-Za-z]*)"
    schedule = re.fullmatch(r"((?:[A-Za-z]+ |[1-9]\d* )?Schedule)(?:,? (?:para|paragraph)\.?\s*" + number + tail + r")?", value, re.I)
    order = re.fullmatch(r"(?:O\.?|Order)\s*" + number + r"(?:\s+r(?:ule)?\.?\s*" + number + tail + r")?", value, re.I)
    unit = re.fullmatch(r"(s(?:ection)?|reg(?:ulation)?|r(?:ule)?|art(?:icle)?|para(?:graph)?)\.?\s*" + number + tail, value, re.I)
    if schedule:
        base = schedule[1].title()
        if schedule[2] is None:
            return base, None, re.escape(base).replace(r"\ ", r"\s+") + r"\b"
        root, suffix, parent, label = base + " para " + schedule[2].upper(), schedule[3], base, schedule[2].upper()
    elif order:
        base = "O " + order[1].upper()
        if order[2] is None:
            return base, None, r"(?:ORDER|O\.?)\s*" + re.escape(order[1]) + r"\b"
        root, suffix, parent, label = base + " r " + order[2].upper(), order[3], base, order[2].upper()
    elif unit:
        aliases = {"section": "s", "regulation": "reg", "rule": "r", "article": "art", "paragraph": "para"}
        kind = aliases.get(unit[1].lower(), unit[1].lower())
        root, suffix, parent, label = kind + " " + unit[2].upper(), unit[3], None, unit[2].upper()
    else:
        raise ValueError("unsupported provision locator; use e.g. s 9A(2)(b), reg 4(1), O 9 r 1(2), or First Schedule para 2")
    if suffix:
        tokens = re.findall(r"\(([A-Za-z0-9]+)\)", suffix)
        parent = root + "".join("(" + t + ")" for t in tokens[:-1])
        label_pattern = re.escape("(" + tokens[-1] + ")")
    else:
        # A top-level numbered unit must carry its source number and delimiter.
        label_pattern = re.escape(label) + r"(?:\.|[—–])"
    return root + suffix, parent, label_pattern


def canonical_provision(value):
    return provision_locator(value)[0]


def build_provisions(text, manifest):
    """Bind reviewed hierarchical locators to original text, preserving whole units."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("provisions"), list) or not manifest["provisions"]:
        raise ValueError("provision map needs a non-empty provisions array")
    rows, by_locator = [], {}
    for item in manifest["provisions"]:
        if not isinstance(item, dict):
            raise ValueError("malformed provision map entry")
        locator, parent, label = provision_locator(item.get("locator"))
        if locator in by_locator:
            raise ValueError("duplicate provision locator in source map")
        start, end = item.get("start"), item.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("invalid provision source span")
        passage = text[start:end]
        label_match = re.match(label, passage, re.I)
        if not label_match:
            raise ValueError(f"{locator}: source span does not begin with the correct provision label")
        if not re.search(r"[^\s.—–:\-]", passage[label_match.end():]):
            raise ValueError(f"{locator}: source span contains only a label, not the provision text")
        if item.get("status") not in ("in-force", "partly-in-force", "not-in-force", "repealed", "uncertain") or not isinstance(item.get("status_note"), str) or not item["status_note"].strip():
            raise ValueError(f"{locator}: record provision-specific operative status and status_note")
        row = {"locator": locator, "parent": parent, "start": start, "end": end,
               "text": passage, "status": item["status"], "status_note": item["status_note"]}
        rows.append(row)
        by_locator[locator] = row
    for row in rows:
        if row["parent"]:
            parent = by_locator.get(row["parent"])
            if parent is None or not parent["start"] <= row["start"] < row["end"] <= parent["end"]:
                raise ValueError(f"{row['locator']}: capture its complete parent provision and keep the child inside it")
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            if left["start"] < right["end"] and right["start"] < left["end"]:
                def ancestor(a, b):
                    parent = b["parent"]
                    while parent:
                        if parent == a["locator"]:
                            return True
                        parent = by_locator[parent]["parent"]
                    return False
                if not ancestor(left, right) and not ancestor(right, left):
                    raise ValueError("unrelated/sibling provision spans overlap; check the boundaries")
    return rows


def checked_provisions(source, text):
    index = source.get("provision_index")
    if not isinstance(index, dict) or index.get("boundaries_reviewed") is not True or not isinstance(index.get("review_note"), str) or not index["review_note"].strip():
        raise ValueError("statutory evidence needs a provision index with reviewed boundaries")
    if index.get("text_sha256") != source.get("text_sha256"):
        raise ValueError("provision index refers to a different text snapshot")
    expected = build_provisions(text, index)
    if expected != index.get("provisions"):
        raise ValueError("provision index does not match source labels, full text and offsets")
    return expected


def select_provision(rows, locator):
    locator = canonical_provision(locator)
    by_locator = {p["locator"]: p for p in rows}
    if locator not in by_locator:
        raise ValueError("cited provision is missing from the reviewed source map")
    selected, context = by_locator[locator], []
    parent = selected["parent"]
    while parent:
        context.insert(0, dict(by_locator[parent]))
        parent = by_locator[parent]["parent"]
    return [dict(selected)], context


def verify_statute_receipt(data, source):
    receipt = source.get("statute_verification")
    if not isinstance(receipt, dict):
        raise ValueError("legislation needs a fresh statute_verification receipt")
    for field in ("identity_note", "version_note", "commencement_note"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError(f"statute_verification needs {field}")
    if receipt.get("instrument_kind") not in ("act", "subsidiary-legislation", "constitution", "other-written-law"):
        raise ValueError("identify whether the instrument is an Act, subsidiary legislation or other written law")
    if receipt.get("instrument_title") != source.get("title") or receipt.get("instrument_citation") != source.get("citation"):
        raise ValueError("statute_verification does not identify the actual source instrument")
    if receipt.get("source_version") != source.get("version"):
        raise ValueError("statute_verification does not match the actual source version")
    if not data.get("run_id") or receipt.get("run_id") != data["run_id"] or receipt.get("checked_on") != data.get("research_date"):
        raise ValueError("statute identity and version must be rechecked for this run and research date")
    draft_hash = data["draft"].get("sha256") if isinstance(data.get("draft"), dict) else None
    if receipt.get("draft_sha256") != draft_hash:
        raise ValueError("statute_verification belongs to a different draft snapshot; recheck this fresh draft")
    if not isinstance(receipt.get("law_as_at"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", receipt["law_as_at"]):
        raise ValueError("statute_verification needs its selected law_as_at date")
    date.fromisoformat(receipt["law_as_at"])
    return receipt
