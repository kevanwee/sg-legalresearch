# Process model review

Reviewed **20 October 2026** against the skill workflow and offline helper behaviour.
The SVG is a descriptive model of the saved-run research/cite-check path, not an
executable BPMN definition or an enterprise process architecture.

## Findings in the previous diagram

| Finding | Effect | Correction |
|---|---|---|
| The Sources lane contained “Retrieve primary material”. | The publisher appeared to perform work actually initiated by the agent. | Keep retrieval with the agent; show publishers as external context. |
| No start or end events. | Process boundaries were implicit. | Show a supplied request at the start and lawyer-controlled completion at the end. |
| “Pass status?” appeared in the helper lane. | Mechanical output and the agent's readiness decision were conflated. | Helpers return results; the agent routes errors to correction and valid records to delivery. A pass-with-limits can proceed with limits disclosed. |
| Correction returned to capture without an explicit correction activity. | The model hid the work to fix extraction, evidence or review errors. | Assign correction to the agent and repeat capture, assessment and checks. A changed draft requires a fresh run. |
| Source unavailability was a footer note only. | The normal path implied retrieval always succeeds. | Describe a retrieval subprocess with independent-source fallback and an unresolved-gap outcome. |
| Court checks and delivery sat at the same detail level as helper operations. | The model mixed skill execution and downstream professional work. | Group applicable professional checks in a lawyer-owned subprocess, expanded below. |

## Scope and responsibility

The process starts with a lawyer-supplied question or preserved draft and ends with
the lawyer's decision and controlled delivery. Research and cite-check differ in
planning inputs: an issue map versus a draft-location inventory. Their shared
retrieval, evidence and review sequence is shown once.

The lawyer controls scope, acceptance, professional checks and sending. The agent
discovers access, retrieves, interprets, prepares records, resolves errors and reports
limits. Offline helpers execute snapshot/index/quote/consistency operations under
agent invocation. They do not browse or decide legal merits. Publishers are external
sources; a retrieved document is a work product, not a process instruction.

## Collapsed subprocesses and routing rules

**Retrieve needed sources:** discover usable session tools; choose a permitted
route; retrieve the exact cited authority and version. On unavailability or refusal,
use relevant independent sources and already supplied copies. If needed, request an
exact manually saved view. If required text or its operative version remains
unverified, retain a gap and leave the affected legal conclusion unresolved. Respect
tool-enforced stops. See [source access](../skills/singapore-legal-research/references/sources-authority.md#access-and-retrieval-conduct)
and [issue #15](https://github.com/kevanwee/sg-legalresearch-skill/issues/15).

**Correct evidence and records:** repair against the original source, not by
changing numbering to make checks pass. Rebuild affected indexes and repeat legal
assessment and checks. Genuine unavailable evidence is a disclosed limit; it does
not justify fabricated data or an indefinite retry loop. A materially changed draft
starts a fresh run and renewed identity/version checks.

**Applicable professional checks and delivery:** the lawyer completes authorised
citator/treatment checks where available, applicable Practice Directions and format
requirements, professional sign-off, then filing, service or sending where relevant.
The skill performs none of those external actions automatically. A request for more
research returns to the agent. A lawyer can also accept a report that transparently
records unresolved questions without treating them as verified advice.

## Analysis and next improvements

Separate observed defects, causes and proposed solutions. Source access is an
availability/permission constraint; extraction defects are system-function defects;
misassigned tasks and hidden loops are modelling defects. Redrawing an arrow does
not fix a missing integration or a publisher constraint.

For future runs, measure time to the first usable authority, waiting time versus
active retrieval time, proportion of decisive provisions with a verified operative
version, unresolved-source rate, extraction corrections per source and repeat-review
cycles. Establish a baseline before claiming a bottleneck or faster delivery.
These are proposed measurements, not implemented telemetry or measured benefits.

For solutioning, separate existing functions (snapshot, paragraph/provision lookup,
quote checks, consistency checks) from agent/tool-dependent retrieval and proposed
connectors. Source proposals should satisfy issue #15's acceptance criteria; the
diagram must not imply that a universal statute API already exists.

Notation uses the basic task/event/gateway/lane distinctions in the
[OMG BPMN 2.0.2 specification](https://www.omg.org/spec/BPMN/2.0.2/).
The illustration collapses detailed subprocesses and supplies their business rules
here; it does not claim full BPMN interchange or execution conformance.
