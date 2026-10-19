# Statutory provision evidence and fresh-draft verification

Apply this to Acts, the Constitution and subsidiary legislation. The two directions
are the same as for judgments: research retrieves the precise operative provision
before citing it; cite-checking starts with the provision actually cited in the draft
and tests that provision against the proposition or quotation.

## Identify the instrument before checking its section

For every fresh document, identify each statutory citation from its full title,
year, historical chapter/edition where relevant, and any abbreviation defined in
that draft. Resolve short forms within this document; do not reuse another matter's
abbreviation mappings. Verify that the source is the intended Act, Constitution,
regulation, rule or order. A similarly named statute, a predecessor Act, a different
year's re-enactment, an amending Act and the principal Act are distinct instruments.
An Act and regulations under it are not interchangeable just because a provision
number matches. Check the actual citation provision and official identifier.

Then establish the date governing the proposition from the events and issues in
the draft. **Do not automatically select today's law.** Retrieve the corresponding
SSO/Gazette version, check the particular provision's commencement and operative
status, amendments, savings and transitional provisions, and any renumbering or
re-enactment. Follow [statutes and revised editions](statutes-revised-editions.md).
The revised-edition year is not a current-through date or proof of commencement.

Create a fresh run for a fresh or materially revised document. Existing downloads
can be consulted, but their prior identity/version findings are not automatically
verified for this draft. Record the checks actually repeated and unresolved access
gaps. Do not stamp a cached document as current because its title looks right.

## Capture the exact unit and its context

Retain the complete cited section/subsection/paragraph with its source offsets,
version and official numbering, including for a paraphrase. For `s 9A(2)(b)`, also
retain the full enclosing `s 9A(2)` and `s 9A` as context so the lead-in, qualifications
and sibling exceptions can be read. Retrieve relevant definitions, schedules and
cross-referenced provisions separately. Parent context does not authorise quoting
an uncited sibling as if it came from the cited leaf provision.

The helper uses a **reviewed provision map**, not a universal statutory-layout parser.
Obtain the hierarchy and complete boundaries from the actual source or a documented
structural extraction, then map locators to zero-based Python string offsets in the
saved UTF-8 text. Never substitute PDF viewer coordinates or a search-result snippet.
The span begins with the unit's real label, e.g. `9A.` or `(b)`. Preserve the complete
unit through its actual end. Review notes, amendments, tables and trailing material
when deciding its boundary; a text-span check cannot determine completeness by itself.

The map has a non-empty `provisions` array. Each entry contains:

```json
{
  "locator": "s 9A(2)(b)",
  "start": 100,
  "end": 180,
  "status": "in-force",
  "status_note": "Record the actual provision-level commencement and operative-status check."
}
```

Those offsets are illustrative, not usable source evidence. Include every ancestor
unit in the same map, each with its own full span. The helper computes parent paths,
checks the source label, enforces containment, and rejects overlapping unrelated
units. Statuses are `in-force`, `partly-in-force`, `not-in-force`, `repealed` and
`uncertain`. A status note is required for each unit; do not rely solely on the Act's
original commencement date. Non-operative/uncertain units remain visible limitations.

Supported locator forms include `s 9A(2)(b)`, `reg 4(1)`, `r 12(3)`, `art 4`,
`O 9 r 1(2)`, and `First Schedule para 2(1)(a)`; single-unit long forms such as
`section 9A(2)` are accepted. Unsupported layouts or locator syntax require manual
review and a disclosed limitation, not invented labels. Split multi-section/range
citations into individual provision findings; do not silently truncate a range.

## Verify identity and version for this run and draft

The map also includes `statute_verification`:

```json
{
  "run_id": "copy the current run_id from run.json",
  "draft_sha256": null,
  "instrument_title": "Synthetic Act 2000",
  "instrument_citation": "SYNTHETIC-ACT-1",
  "instrument_kind": "act",
  "source_version": "copy the actual source version from run.json",
  "law_as_at": "2026-10-20",
  "checked_on": "2026-10-20",
  "identity_note": "Explain the title, year, identifier and instrument-type comparison.",
  "version_note": "Explain why this selected version governs the relevant events.",
  "commencement_note": "Explain provision-level commencement, amendments, savings and transition checks."
}
```

This is a synthetic template. Use the actual title and identifier from the source,
and match `source_version` to its actual recorded version; changing a version label
without a corresponding fresh verification record fails the check. Use
actual dates, and factual check notes. `instrument_kind` is `act`,
`subsidiary-legislation`, `constitution` or `other-written-law`. For a Word draft,
`draft_sha256` must equal the current run's `draft.sha256`; null applies only when no
draft snapshot is attached. `run_id` and `checked_on` must match the current run and
research date. A stale receipt or another draft's hash fails; attaching a draft after
verification requires rechecking and a receipt tied to that snapshot. These bindings
record the review, not proof that a reviewer actually performed it.

```sh
python skills/singapore-legal-research/scripts/research.py index-provisions runs/matter --source L1 --map provision-map.json --confirm-boundaries --review-note "Checked complete provision boundaries and hierarchy against the selected official version"
python skills/singapore-legal-research/scripts/research.py provision runs/matter --source L1 --locator "s 9A(2)(b)"
```

The `provision` command returns an evidence object with the selected full `passages`,
separate ancestor `context`, exact locator, and verified source date. Add it to the
claim and complete `support_note` and `pinpoint_reviewed` after legal review. The
command leaves that review flag false. The reference's `law_as_at` must match its
source receipt; when it differs from the run's default date, add `date_basis` explaining
the relevant event date or the historical comparison. Keep different versions under
different source IDs, each with its own snapshot, map and fresh receipt.

## Cite-check the original statute, version and provision

Preserve the literal draft citation in `citation_check`, as with case citations.
In addition to `source_id`, `citation`, `pinpoint`, `result` and `reason`, record:

- `resolved_instrument`: the actual source title after resolving the draft's name or abbreviation.
- `instrument_result`: `matched`, `wrong-instrument`, `ambiguous` or `unverifiable`, plus `instrument_note`.
- `version_result`: `matched`, `wrong-version` or `unverifiable`, plus `version_note`.
- `applicable_on`: the date governing this proposition, plus `date_basis` explaining it.

A supported finding requires matched instrument and version, the source verified for
that applicable date, and the exact cited provision in the evidence. Retain the
original wrong section or historical version as comparison evidence; capture any
proposed correction separately. Use distinct `wrong-instrument`, `wrong-version`,
`wrong-pinpoint`, `unsupported`, `missing-pinpoint` and `unverifiable` findings. A
defective or unverified citation cannot be marked supported. If the original source
cannot be identified or retrieved, use an unresolved finding with the exact citation
and obstacle; never manufacture a map or receipt merely to pass the checker.

For shorthand such as the second provision in `ss 9A and 9B`, retain the literal
locator fragment as `pinpoint`, provide `resolved_pinpoint` such as `s 9B`, and add
`pinpoint_resolution_note` explaining its antecedent and unit. Each cited provision
still needs its own finding. Do not confuse a change in numbering with a change in law.

The checker verifies the source spans, hierarchy, receipt bindings, dates and declared
review fields. The agent must still assess whether the operative wording supports
the draft's proposition, read definitions/exceptions, and verify the publication and
version metadata against official material. It does not infer statutory meaning or
commencement from the text offsets, nor certify the authenticity of a supplied file.
