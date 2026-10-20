# v0.2.1 release review

Reviewed **20 October 2026**. This is a policy release. It changes how the skill retrieves
Singapore Statutes Online (SSO) provisions outside 3 a.m. to 7 a.m. Singapore time. No helper,
converter or evidence check changes.

## Change since v0.2.0

- **Real-browser SSO reading at any hour.** Under a maintainer policy recorded in
  [access and retrieval conduct](../skills/singapore-legal-research/references/sources-authority.md#access-and-retrieval-conduct),
  an agent-operated real browser may read the SSO provision views, or the single Act or
  version download, that a question needs at any hour, at reading pace, keeping copies only
  as private research evidence.
- **Scripted and bulk collection unchanged.** Script requests, harvesting beyond the
  question, corpus building and repeated collection stay within the 3–7 a.m. window with
  honest identification. A refused scripted client is never disguised as a browser.
- **Recorded as a reading, not a permission.** The policy is the maintainer's reading of the
  [SSO Terms of Use](https://sso.agc.gov.sg/Terms-of-Use), not AGC's classification of
  agent-assisted reading; AGC permission would supersede it. Each source's `review_note`
  records the route used, so a reviewer can see which policy applied.

## Why

Under v0.2.0, statutory research outside the window depended on independent sources and
user-saved copies. Where those could not establish the operative version, statutory claims
stayed `limited`. Real-browser reading restores runtime access without scripts or spoofing.

## Validation

The synthetic suite and repository checks pass (`python -m unittest discover -s tests`,
`python scripts/validate_repository.py`). The change is to instructions only; it was not
exercised against live SSO in this review. Live statutory access and operative-version
verification remain tracked in
[issue #15](https://github.com/kevanwee/sg-legalresearch-skill/issues/15).
