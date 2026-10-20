# v0.1.0 release review

Reviewed on 20 October 2026 for an initial public release of the Singapore legal
research skill. The release supports supervised research and source verification;
it is not a standalone legal database, automated citator or filing service.

## What is included

- A self-contained skill for local Codex and Claude Code installations.
- Singapore primary-source, citation, statute-version and Hansard research protocols.
- Case-law evidence bound to complete cited paragraphs, including for paraphrases.
- Statutory evidence bound to the precise instrument, applicable version and unit,
  with parent context and fresh-draft verification records.
- An offline Python 3.11+ CLI for snapshots, Word inventories, evidence checks and
  reviewed CSL-JSON export; no third-party Python packages are required.
- Source/authority Mermaid diagrams and an editable workflow swimlane.

## Release checks

The release review covers skill instructions and reference routing, agreement
between documented evidence requirements and helper checks, installed-copy packaging,
isolated execution, repository hygiene, installation instructions and diagram layout.

The automated suite contains 117 tests using synthetic sources and documents. The
whole suite is also run with `python -I`; copied installations are exercised with
`-I`, `-P` and `PYTHONSAFEPATH=1`, including an unrelated `statutory.py` on `PYTHONPATH`.
Repository and skill metadata validators check the published files. Linux/Windows CI
uses Python 3.11 and 3.13; local validation uses Python 3.14.2. Release archives are
checked separately by extraction and installed-helper startup.

Installation locations were compared with the [official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills)
and [Claude Code skill documentation](https://code.claude.com/docs/en/skills).
[AGC's revision guidance](https://www.agc.gov.sg/our-roles/drafter-of-laws/revised-editions-of-legislation/)
and the [Judiciary's Supreme Court overview](https://www.judiciary.gov.sg/who-we-are/role-structure-supreme-court)
were reopened during review. This is not fresh substantive verification of every
linked authority or live statute; each research run must still verify its own official
instrument and date. The SSO and eLitigation terms of use and SSO's `robots.txt` were
read on 20 October 2026 for the access and retrieval conduct rules.

## Live-source trial

Before this release the skill was run end to end on real public sources: a research
memo on copyright infringement under the Copyright Act 2021 and *Global Yellow Pages
Ltd v Promedia Directories Pte Ltd* [2017] SGCA 28, and a cite-check of a synthetic
draft with planted errors. All planted errors were caught. The trial found and fixed:

- **Windows output encoding.** The CLI crashed when a captured passage contained a
  character outside the console code page (SSO text uses U+2011) and output was piped.
  It now always writes UTF-8.
- **SSO headings ending in "etc."** A correct statutory map was refused because the
  next section's heading ended with "etc."; such headings are now valid boundaries.
- **Retrieval conduct.** Scripted SSO requests during the trial triggered a firewall
  challenge. The skill now follows SSO's terms (automated extraction only 3–7 a.m.
  Singapore time, honest identification, no circumvention). It retrieves first through
  an agent-operated real browser at reading pace with no stealth, which loaded SSO
  normally in testing, including historical versions; then pages the user saves; then
  scripted requests within the terms. It stops on a block.

## Boundary hardening before this release

Recognised separate note blocks now stop judgment indexing instead of being absorbed
into the last paragraph. This covers note headings and explicit line-start note
markers; inline references remain intact. Notes must be retained separately, with
a documented body extraction. Older merged indexes receive the same checks. Prose
that merely mentions a footnote, such as `Footnote 3 of the submissions`, is not
treated as a note block.

Statutory maps now reject ends that leave continuation prose before the next unit
boundary, including mid-word, mid-sentence and wrapped-line cutoffs, and a unit cut
before its own unmapped sub-units. An unmapped child label is a boundary only when
it is the next sibling in the unit's or an ancestor's series, including inserted
units such as `(ba)` and `(2A)`. The next section's heading line and line-only
amendment notes such as `[23/2018]` do not cause false refusals. A parent's closing
words, provisos, Explanations or Illustrations are declared with `tail_start`, so a
child ends cleanly without being stretched over its parent's text. The validation uses
source spans and unit boundaries rather than sentence punctuation. Existing saved
indexes are revalidated. Valid colons, semicolons and partial maps remain usable.

## Known limits

- Conversion may already have erased note markers, removed a final paragraph or
  truncated the saved source itself. Flattened text alone cannot prove what is absent.
  Compare against original HTML/PDF structure; disclose unresolved boundaries.
- Unsupported statutory layouts and definition-specific locators require the documented
  parent-subsection or manual-verification approach. A recognised label alone does
  not establish legal hierarchy or authenticity. Text alone cannot tell a roman `(i)`
  sub-limb from the letter after `(h)`; check that boundary against the source.
- Unmarked trailing notes, signatures or annexes after a judgment's last paragraph
  are not detected; inspect the end of each saved judgment text.
- A helper pass checks evidence records and declared review. The agent/reviewer still
  decides proposition support, operative law, ratio/obiter, treatment and legal effect.
- Public treatment searches do not establish comprehensive citator coverage. Subscription
  access, official-site availability and the agent's research tools affect coverage.
- Tests do not benchmark live end-to-end legal accuracy or professional suitability.

## Install and artifacts

Follow the [README installation steps](../README.md#install). The release tag pins
the reviewed source. GitHub's source archive includes the installer, documentation
and tests. The compact `singapore-legal-research-v0.1.0.zip` contains only the
self-contained skill folder and its MIT licence for manual installation; its SHA-256
checksum is supplied in `SHA256SUMS.txt`. No private runs, downloaded authorities,
style-guide PDFs, credentials or local tooling belong in either archive.
