# Contributing

Contributions should make Singapore legal research easier to verify. Start with a
reproducible problem or a concrete workflow improvement. See
[open issues](https://github.com/kevanwee/sg-legalresearch-skill/issues), especially
[statutory-source access and version verification (#15)](https://github.com/kevanwee/sg-legalresearch-skill/issues/15).

## Set up and validate

Use Python 3.11 or newer. Bundled helpers use only the standard library; no package
installation is needed for these checks:

```sh
git clone https://github.com/kevanwee/sg-legalresearch-skill.git
cd sg-legalresearch-skill
git switch -c fix/describe-the-change
python -m unittest discover -s tests -v
python scripts/validate_repository.py
```

Keep the installed skill self-contained under `skills/singapore-legal-research/`.
Root-level documentation, tests and installer tools must not become runtime
dependencies. Exercise copied installations from another directory under `python -I`
when changing imports, packaging or CLI behaviour. CI checks Windows and Linux on
Python 3.11 and 3.13.

## Report a bug or propose a source

Include the commit/version, Python version, operating system, exact command or
workflow, expected result and actual result. For source access, distinguish an absent
tool, empty inventory, attachment failure, site refusal and readable live content.
Include date, URL, route and selected statutory version where known. Do not post
credentials, session tokens, private screenshots or client documents.

For an additional statutory source, identify publisher, provenance, coverage,
consolidation/edition date, access conditions, historical-version support and
commencement evidence. A snippet or link to SSO is not a retrieved independent copy.
Do not describe an older copy as current without checking amendments and commencement.
Follow the [source workflow](skills/singapore-legal-research/references/statute-source-fallbacks.md).

## Change and test

- Use clearly labelled synthetic fixtures. Keep client documents, live research
  runs, downloaded authorities, course decks, third-party PDFs and credentials out
  of commits. An ignored file is not permission to publish its contents elsewhere.
- For extraction bugs, reproduce the failing structure and assert complete passage
  contents, boundaries and source labels. Equal paragraph counts do not establish
  completeness. Exercise conversion through indexing and quotation where a wrong
  pinpoint could result; test failure paths and relevant prior regressions.
- After code changes, run `python -m unittest discover -s tests -v` and
  `python scripts/validate_repository.py`. Explain any failure or check not run.
  Offline fixtures do not establish live browser or statutory-source access.
- Legal guidance must identify its primary authority and verification date.
  Distinguish retrieval, citation identity, quotation fidelity, proposition support
  and subsequent treatment. Scripts cannot establish the last two by themselves.
  A public-web search is not a comprehensive citator check.
- Apply publisher conditions and tool instructions. Record access gaps and use
  permitted independent sources; do not evade blocks or assume browser automation
  is exempt from SSO's collection conditions.
- Keep prose proofreading separate from substantive legal drafting unless requested.

## Documentation and diagrams

Update the relevant skill reference when behaviour changes. Keep process tasks in
the responsible participant's lane; distinguish external publishers, evidence
artefacts and internal execution. Show start/end conditions, conditional routes and
rework. Explain collapsed subprocesses and label future proposals separately from
current behaviour.

Render changed SVGs and inspect labels, arrows, lane boundaries and readability on
a white background. Keep SVG text and shapes editable. A workflow picture is not
proof of an implemented integration, performance gain or BPMN execution conformance.

## Submit a pull request

Describe the problem and resulting behaviour, relevant limitations, tests executed
and any private live checks in summary form. Use synthetic material in the PR.
Link the issue, keep changes focused, and resolve review findings before merge.
Do not upload research evidence merely to demonstrate that a test was performed.
