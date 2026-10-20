"""Offline converters from saved court and legislation pages to evidence text.

They read a page already saved by a browser or other permitted retrieval; they never
fetch anything. Output is structural text for `snapshot --text`; the conversion is a
transformation that still needs review against the original page.
"""

import html as html_module
from html.parser import HTMLParser
import re

ELITIGATION_TRANSFORMATION = (
    "extract-elitigation: numbered Judg-1 paragraphs as [n]; unnumbered paragraphs, "
    "sub-paragraphs and quotations kept as continuation lines of the preceding paragraph; "
    "headings, author lines, signatures and counsel removed; footnote pop-ups moved to a "
    "separate notes file with inline [note: N] markers; whitespace normalised within blocks.")

SSO_TRANSFORMATION = (
    "extract-sso: text of the page's provision container (id=legisContent) only, with tags as "
    "line breaks, split labels such as '(a)' and '146.—(1)' rejoined, and navigation, version "
    "list and footer removed; whitespace normalised within lines.")

NUMBERED = re.compile(r"\s*(\d+)[  \t]+(.*)", re.S)
EXCLUDED = ("Judg-Heading", "Judg-Sign", "Judg-Lawyers", "Judg-EOF")


def clean(text):
    return " ".join(text.replace(" ", " ").split())


class _Judgment(HTMLParser):
    """Collect top-level Judg-* blocks; route footnote modal content to notes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.notes, self.header = [], [], []
        self.cls, self.depth, self.buf = None, 0, []
        self.skip, self.sup, self.note, self.in_header = 0, False, None, 0

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        if self.skip:
            if tag == "div":
                self.skip += 1
                if cls.startswith("FootnoteRef"):
                    self.note = []
            return
        if self.in_header:
            self.in_header += tag == "div"
        elif tag == "div" and cls.startswith("HN-CaseName"):
            self.in_header = 1
        if tag == "div" and self.cls and cls.startswith("modal"):
            self.skip, self.note = 1, None
        elif tag == "sup" and self.cls:
            self.sup = True
        elif tag == "div":
            if self.cls is None and cls.startswith("Judg-"):
                self.cls, self.depth, self.buf = cls.split()[0], 1, []
            elif self.cls is not None:
                self.depth += 1
        elif tag == "br" and self.cls:
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if self.skip:
            if tag == "div":
                self.skip -= 1
                if self.skip == 0 and self.note is not None:
                    self.notes.append(clean("".join(self.note)))
                    self.note = None
            return
        if self.in_header and tag == "div":
            self.in_header -= 1
        if tag == "sup":
            self.sup = False
        elif tag == "div" and self.cls is not None:
            self.depth -= 1
            if self.depth == 0:
                self.blocks.append((self.cls, "".join(self.buf)))
                self.cls = None

    def handle_data(self, data):
        if self.skip:
            if self.note is not None:
                self.note.append(data)
            return
        if self.in_header:
            self.header.append(data)
        if self.cls and self.sup:
            if data.strip():
                self.buf.append(f"[note: {data.strip()}]")
        elif self.cls:
            self.buf.append(data)


def extract_elitigation(html):
    """Return opinions (each with [n] paragraph text), separated notes and a reconciliation report."""
    parser = _Judgment()
    parser.feed(html)
    opinions, current, report = [], None, {
        "html_numbered_blocks": 0, "spacer_blocks": 0, "continuation_blocks": 0,
        "excluded_blocks": 0, "warnings": []}

    def start_opinion(author):
        nonlocal current
        current = {"author": author, "lines": [], "numbers": []}
        opinions.append(current)

    for cls, raw in parser.blocks:
        if cls == "Judg-Author":
            if current is None or current["numbers"]:
                start_opinion(clean(raw))
            else:
                current["author"] = clean(raw)
            continue
        if cls.startswith(EXCLUDED):
            report["excluded_blocks"] += 1
            continue
        match = NUMBERED.match(raw) if cls == "Judg-1" else None
        if match:
            report["html_numbered_blocks"] += 1
            number = int(match[1])
            if current is None:
                start_opinion("")
            elif current["numbers"] and number == 1:
                start_opinion("")
                report["warnings"].append("paragraph numbering restarted without an author line; "
                                          "treated as a separate opinion")
            elif current["numbers"] and number != current["numbers"][-1] + 1:
                report["warnings"].append(f"numbering gap: [{current['numbers'][-1]}] then [{number}]")
            current["numbers"].append(number)
            current["lines"].append(f"[{number}] {clean(match[2])}")
            continue
        if current is None or not current["numbers"]:
            continue  # Front matter before the first numbered paragraph.
        text = clean(raw)
        if cls.startswith("Judg-Quote"):
            if text:
                current["lines"].append("    " + text)
                report["continuation_blocks"] += 1
        elif cls in ("Judg-1", "Judg-2", "Judg-3", "Judg-4"):
            if text:
                current["lines"].append(text)
                report["continuation_blocks"] += 1
            else:
                report["spacer_blocks"] += 1
    opinions = [o for o in opinions if o["numbers"]]
    if not opinions:
        raise ValueError("no numbered judgment paragraphs found; check that this is a saved eLitigation judgment page")
    extracted = sum(len(o["numbers"]) for o in opinions)
    if extracted != report["html_numbered_blocks"]:
        report["warnings"].append("extracted paragraph count differs from numbered blocks in the page")
    for opinion in opinions:
        numbers = opinion["numbers"]
        if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
            report["warnings"].append(f"opinion '{opinion['author']}' numbering is not consecutive")
    return {"header": clean(" ".join(parser.header)),
            "opinions": [{"author": o["author"], "first": o["numbers"][0], "last": o["numbers"][-1],
                          "paragraphs": len(o["numbers"]), "text": "\n".join(o["lines"]) + "\n"} for o in opinions],
            "notes": [f"[note: {i}] {n}" for i, n in enumerate(parser.notes, 1)],
            "report": dict(report, extracted_paragraphs=extracted)}


def _flat(fragment):
    return html_module.unescape(re.sub(r"<[^>]+>", " ", fragment))


def extract_sso(page):
    """Return SSO provision text plus the page's title, version status and Act amendment list."""
    start = page.find('<div id="legisContent">')
    if start < 0:
        raise ValueError("no SSO provision content found (id=legisContent); save the provision view of the page")
    body = page[start:]
    footer = re.search(r'<footer|<div[^>]*class="[^"]*footer', body)
    body = body[:footer.start()] if footer else body
    text = html_module.unescape(re.sub(r"<[^>]+>", "\n", body))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = re.sub(r"\(\n(\w+)\n\)", r"(\1)", text)          # "(\na\n)" -> "(a)"
    text = re.sub(r"^(\d+[A-Z]*\.)\n(—)", r"\1\2", text, flags=re.M)  # "146.\n—(1)" -> "146.—(1)"
    text = re.sub(r"\n([),;.])", r"\1", text)               # stray punctuation lines
    text = text.strip() + "\n"
    flat = " ".join(_flat(page).split())
    title = re.search(r"<title>\s*(.*?)\s*(?:-\s*Singapore Statutes Online)?\s*</title>", page, re.S)
    status = re.search(r"Status:\s*(.+?)\s+Print\b", flat)
    sections = re.findall(r"^(\d+[A-Z]*)\.(?:—|\s)", text, re.M)
    warnings = []
    if not status:
        warnings.append("no version status line found; record the version from the page manually")
    if not sections:
        warnings.append("no numbered provision found in the content; check the saved view")
    return {"title": " ".join(title[1].split()) if title else "",
            "status": status[1] if status else "",
            "act_amendments": [{"date": d, "by": act} for d, act in
                               re.findall(r"(\d{2} \w{3} \d{4}) Amended by (Act \d+ of \d{4})", flat)],
            "provisions": sections, "text": text, "warnings": warnings}
