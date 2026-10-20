# v0.2.0 release review

Reviewed **20 October 2026**. This release adds saved-page converters, precise
quotation lookup and extraction hardening, plus clearer source-access and contributor
guidance. It supports supervised research and cite-checking within the documented
limits. It does not guarantee universal live statutory access.

## Changes since v0.1.0

- Saved eLitigation HTML conversion separates opinions, footnotes, annexes and other
  trailing material. Reports reconcile block types, footnote identifiers and missing
  or conflicting note definitions. Inline spans preserve words; block boundaries
  preserve separators. Numbered `Judg-List-*` blocks remain in their parent paragraph.
- Detached paragraph labels stop conversion before output. Mixed bare-label formats
  also stop indexing and rechecking older saved indexes, closing a terminal-label
  wrong-pinpoint path with no later numbering gap.
- Saved SSO provision views are extracted through an HTML parser selecting the
  complete `legisContent` subtree, independent of attribute order or quoting. Siblings
  outside that element stay outside the extracted provision text.
- The `quote` command searches only the cited paragraphs or provisions. Disjoint
  ranges do not include intervening paragraphs. Sub-paragraph pinpoints retain their
  literal form and explicitly warn that lookup searches the whole numbered paragraph;
  the reviewer must check the specific sub-paragraph.
- Live workflows discover available browser routes before declaring access
  unavailable. Independent statutory-source fallbacks distinguish retrieval from
  operative-version verification. Source access remains subject to tool instructions
  and publisher conditions.
- [CONTRIBUTING.md](../CONTRIBUTING.md) documents setup, tests, source proposals and
  privacy rules. The [process model](diagrams/skill-workflow.svg) and
  [review](process-model-review.md) clarify ownership, events, decisions, corrections
  and downstream professional work.

## Validation and evidence

The 167-test synthetic suite passes locally on Python 3.14. CI checks Windows and
Linux with Python 3.11 and 3.13. Tests include copied installations, isolated/safe-path
startup, conversion through snapshot/index/quotation, detached terminal labels,
previously merged indexes, complete lists, annex boundaries, note reconciliation and
SSO container boundaries. Repository metadata, syntax, links and fences are checked.
The process SVG was rendered in Chrome and visually inspected.

Private checks against previously retrieved official judgment HTML compared full
contents rather than paragraph counts alone. Shopee's 94 paragraphs match the earlier
reviewed extraction; all 22 list blocks across [3], [13], [31], [34], [37] and [53]
are retained, and each can be located at its correct paragraph. Boston Scientific's
67 paragraphs also match. JGP retains 112 paragraphs with its final paragraph at
737 characters and its annex separate. These were saved-source regression checks,
not fresh live retrieval or independent benchmarking of legal accuracy. Downloaded
authorities and private runs are excluded from release assets.

## Statutory access remains an open constraint

[Issue #15](https://github.com/kevanwee/sg-legalresearch-skill/issues/15) tracks live
access and operative-version verification. Direct web-reader access returned HTTP
403 in the latest review. The [SSO Terms of Use, cl 13(d)](https://sso.agc.gov.sg/Terms-of-Use)
and [FAQ A3(d)](https://sso.agc.gov.sg/FAQ) review used publisher text returned by
search; it did not verify a current statutory provision.

Ordinary manual browsing is distinct from automated collection. The skill applies
the 3–7 a.m. Singapore-time condition to agent collection through browsers and scripts
unless applicable AGC permission or clarification supports a different use. This is
the skill's conservative interpretation; the examined wording contains no express
agent-browser exemption. See the maintained [retrieval guidance](../skills/singapore-legal-research/references/sources-authority.md#access-and-retrieval-conduct).
Outside that window or when SSO is unavailable, use permitted independent sources or
user-saved copies. An old text or amendment is not automatically a current
consolidation. Unverified operative versions remain visible and unresolved.

## Other material limits

- Older p-based judgment HTML needs documented manual extraction. Detached labels
  require source-reviewed correction rather than automatic guessing.
- Unmarked trailing material whose structure was already lost, and source files
  already truncated at EOF, still require comparison with the original.
- Statutory provision maps require complete units and source-reviewed hierarchy.
  Definition-specific locators and parent lead-in quotations follow the documented
  whole-unit/manual-verification rules.
- A helper pass establishes record consistency and declared review, not proposition
  support, legal correctness, current law or comprehensive subsequent treatment.
  Authorised report/citator access and applicable professional checks remain separate.

## Install and update

Follow the [installation guide](../README.md#install). GitHub's source archives
include the installer, documentation and tests. The compact
`singapore-legal-research-v0.2.0.zip` contains the self-contained
`singapore-legal-research/` folder plus the MIT licence for manual copying.
`SHA256SUMS.txt` records the compact archive's SHA-256 checksum.

Existing installations are not overwritten automatically. Back up local changes
outside skill-discovery folders, replace the entire installed skill, and restart
the agent session. Updating a repository clone alone does not update its installed copy.
