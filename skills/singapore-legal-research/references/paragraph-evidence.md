# Paragraph evidence: research and cite-checking

## Two directions, one source passage

**Research:** proposition → authoritative judgment and version → complete supporting
paragraphs → case citation with the actual pinpoint. This applies to paraphrases as
well as quotations. A case existing does not establish that it supports the proposition.

**Cite-check:** exact citation in the draft → its identified judgment/version → its
specifically cited paragraphs → comparison with the draft's proposition or quotation.
Finding the same words somewhere else in the case does not verify that pinpoint.

Read the complete cited paragraphs and nearby context. Identify who is speaking,
whether the passage states the court's holding, and whether qualifications change its
application. Retain full paragraphs privately in the evidence record; the answer can
use a short extract or paraphrase with a precise citation. Capturing a paragraph does
not require republishing it in full in the final answer or in this public repository.

Use the verified case name and report/neutral citation, followed by the smallest
sufficient locator: `at [35]`, `at [35]–[37]`, or `at [35], [39]`. These numbers
illustrate the format, not an authority. Do not cite a range unless every paragraph
within it was retrieved and read. A page number, PDF viewer page, footnote number and
judgment paragraph number are not interchangeable. The source version must match
the report or judgment actually cited.

## Capture full paragraphs in a saved run

After snapshotting the actual source and any documented text extraction, identify
its explicit line-start paragraph-label format. `bracketed` accepts `[35] Text`;
`numbered` accepts `35 Text` or `35` followed by a tab/em-space and text on the same
line. Wrapped continuation lines are retained. These formats are for judgment
paragraph labels, not the Word draft's paragraph inventory.

```sh
python skills/singapore-legal-research/scripts/research.py index-paragraphs runs/matter --source S1 --style bracketed --confirm-boundaries --review-note "Compared paragraph labels and complete boundaries with the original judgment"
python skills/singapore-legal-research/scripts/research.py passages runs/matter --source S1 --pinpoint "[35]-[37]"
```

Only confirm boundaries after actually reviewing them. Plain-text extraction can
confuse page headers, footnotes, quoted paragraph labels, and the court's own numbering.
Inspect the first/last paragraph and trailing material too; a label parser cannot
know that a footnote or annex belongs outside the last paragraph. Use a better
documented source extraction if boundaries are ambiguous. Never change the court's
numbering to make the helper accept it.

For HTML judgments, inspect the actual document structure. A court's numbered
paragraph may continue through unnumbered blocks, subparagraphs and embedded
quotations before the next numbered paragraph. Selecting only the first numbered
block can omit part of the paragraph. Preserve those continuations and distinguish
quoted paragraph labels from the current court's labels during the documented
conversion; do not flatten every visible number into a new judgment paragraph.

The indexer requires consecutive integer labels (each exactly one greater than the
last) and rejects gaps, duplicates, restarts, out-of-order or lettered labels, and
labels appearing alone on a line. An explicitly captured excerpt can start above 1;
the rule applies between the labels within it. A line containing only `[3]` or `36`
is refused even at the end of the file, rather than absorbed into the preceding
paragraph. The confirmation flag cannot override these checks, including when an
older saved index is revalidated.

If numbering restarts for a separate or dissenting opinion, preserve each opinion
under a separate source ID and paragraph index. Keep the judgment's actual case
name/citation; identify the opinion and judge in the source version/review note and
in the analysis so repeated paragraph numbers are unambiguous. Numbered-style
PDF text can also fail when a wrapped citation starts with `2 SLR 850` or a page
number sits alone on a line. That is an ambiguous extraction, not permission to
renumber the judgment, delete inconvenient labels or silently join lines. Prefer a
documented extraction that preserves the source's actual structural boundaries.
Do not switch to the older-report page fallback merely because a conversion lost
paragraph labels that exist in the original judgment.

These guards do not prove extraction completeness: losing the final label entirely,
or a whole final paragraph, may leave no numbering gap or bare label to detect.
Preserve original HTML paragraph boundaries/identifiers when available, and compare
PDF/text conversions with the source. Source structure is stronger evidence than
guessing boundaries from flattened text; keep the boundary review requirement.

The current helper supports positive integer paragraph numbers only. Unsupported
layouts or labels require manual verification and an explicit unresolved limitation
in the saved run, rather than guessed or silently renumbered passages. The helper
does not fetch a URL or manufacture paragraph text from a search result.

`passages` returns the source identity, citation, version, URL and an `evidence`
object containing each complete paragraph's number, exact text and character offsets
in the saved text. Copy that object into the relevant claim's `evidence` array,
explain its support, and set `pinpoint_reviewed: true` only after checking the legal
locator against the actual judgment. The command leaves that flag false: extracting
text does not constitute legal verification.

`check` regenerates the index from the saved source text and requires a case reference's
`passages` to equal the full paragraph records selected by its `pinpoint`. A cropped
sentence, another paragraph relabelled with the desired number, missing range member,
or changed snapshot fails. A quotation must additionally fall within the cited
paragraphs, not merely match somewhere in the judgment. Disjoint citations cannot
justify a quotation from an intervening uncited paragraph.

## Preserve the citation being checked

One cited authority is one finding; resolve short forms first while keeping their
literal draft text. Each cite-check claim referencing a case needs `citation_check`:

```json
{
  "source_id": "S1",
  "citation": "Synthetic case SYNTHETIC-1 at [1]",
  "pinpoint": "[1]",
  "result": "wrong-pinpoint",
  "reason": "Synthetic example: original paragraph [1] does not support the draft proposition; paragraph [2] is the proposed replacement."
}
```

This example is synthetic, not a Singapore authority. The `citation` must occur in
the claim's inventoried draft location; `pinpoint` preserves its original locator.
Evidence for that original locator must remain separate from evidence for the
replacement, even if both refer to the same case. A `wrong-pinpoint` result requires
both sets of full paragraphs in the evidence array. Explain what the original says
and why the replacement supports the precise proposed wording. If no support is
found, classify the finding as unsupported rather than inventing a correction.

| Result | Required finding |
|---|---|
| `supported` | Exact cited passage supports the proposition/quotation, subject to disclosed qualifications. |
| `wrong-pinpoint` | Original passage checked and does not supply the relied-on support; separately captured replacement paragraphs identified. |
| `unsupported` | Cited passage checked; proposition is not supported there, and no verified replacement is proposed. |
| `missing-pinpoint` | Original citation has no usable locator; retain `pinpoint: ""` and report any proposed locator separately. |
| `unverifiable` | Source/version/paragraph cannot be obtained or reconciled; state the precise obstacle. |

Unverifiable or missing-pinpoint findings may have no source evidence and a null
`source_id` while identification/retrieval is outstanding. Keep their claim assessment
`unresolved` (or `qualified` if verified alternative evidence supports a qualified
conclusion). Defective or unverified citations cannot be marked `supported`. These
classifications are the reviewer's legal assessment, not an automated semantic result.

Present the review with draft location, original citation, proposition or quotation,
cited paragraph text (or an appropriate extract linked to the full private record),
assessment/reason, and any separately labelled proposed correction. Preserve adverse
qualifications and distinguish a wrong pinpoint from a generally false proposition.

## Sources without numbered paragraphs

Older reports may require a report-page locator. For such a case set
`paragraphs_unavailable_reason` on the source, use `locator_type: "page"` on the
evidence reference, and include a `locator_note` describing the actual page check.
Its non-empty `passages` array must retain exact `text`, `start` and `end` in the
saved source. This fallback is unavailable when a numbered-paragraph index exists.
The checker verifies those source spans but reports page-to-text mapping as a manual
limitation; do not claim it inferred the report's printed page from a PDF viewer.

For statutes use [statutory evidence](statutory-evidence.md) to retain the relevant
operative provision, definitions and exceptions with the correct section/rule/regulation,
instrument and version, rechecked for each fresh draft. For Hansard retain the relevant speech
passage with sitting, speaker and actual column/page/available locator. Do not invent
case-style paragraph numbers for these sources. Inaccessible reported text must remain
qualified even if an unreported version is publicly available.
