# Campaign 5 Data-Steward Boundary and Exposure Request

**Prepared 2026-10-19 | Request for source-cited ruling | NOT A DATA AUTHORIZATION**

Campaign 5 remains **NOT AUTHORIZED — DO NOT RUN**. This request does not permit access, copying, hashing, training, scoring, evaluation, integration, or launch. Please answer from authoritative governance, provenance, and access-control records only. Do not open, list, query, hash, or inspect protected evaluation, OOF prediction, prospective, or holdout contents to answer. If the boundary cannot be determined under that constraint, record `NOT DETERMINABLE` and keep it blocked.

## Required decision record

Provide a dated, authenticated determination with citations to exact source records/versions, record owner/custodian, and any disagreements or gaps. For every item, choose `PERMITTED`, `PROHIBITED`, or `NOT DETERMINABLE`, with scope and rationale. A path name or absence from a development copy is not proof of permission or disjointness.

### A. Input identity, operations, and exclusions

1. **Allowlist:** exact dataset/run/artifact IDs, source/version, authorized custodian, and permitted operations (metadata read, byte hash, copy, schema/header read, row read, fit, score, metric computation, output). Identify whether authority applies to canonical source, isolated copy, or both.
2. **Denylist:** exact protected evaluation/OOF/prospective/holdout identifiers and prohibited operations. State whether metadata-only references to these assets are permitted and the approved non-content procedure.
3. **Exclusions:** disallowed rows/periods/artifacts, including previously exposed OOF scores, final calendar strata, any 2025 material, prospective data, labels/targets, model outputs, and any unlinked, synthetic, malformed, duplicate, or immature records. Explicitly distinguish governance metadata from protected content.
4. **Environment controls:** allowed root(s), copy/network/retention/output rules; whether independent reproducibility may use source data or only newly authorized disposable copies; and non-content evidence that protected assets are absent/inaccessible. Name the operator and expiry/revocation mechanism.

### B. Exposure history

Provide a source-backed inventory of who/what previously accessed or viewed protocol-related outcomes: OOF predictions, candidate/experiment results, reported metrics, 2023/2024/2025 strata, validation outputs, labels, and derived summaries. For each exposure state date, actor/process, artifact/period, access type (values, aggregate, header/schema only), and resulting selection/tuning/decision use if known. If unknown, mark unknown—not “unexposed.”

### C. Temporal, group, label-maturity, and purge rules

From the selected source protocol and authoritative data-governance records, specify or mark unresolved:

- Prediction/signal timestamp and feature availability/publication cutoff; event identity and duplicate resolution.
- Target/label definition source, horizon, label validity, label maturity/exit time, delayed corrections and missing/immature-label handling.
- Permitted train/validation periods and calendar cutoffs; chronological ordering; fold coverage; whether any period is previously exposed or can be confirmatory.
- Grouping/independence units: ticker/entity, event family, common date/week/market shock, shared training rows, repeated observations, and any group-disjoint constraints.
- Purge/embargo rules that ensure every training outcome matures before validation prediction time, plus treatment of overlapping horizons/events, inter-fold overlap, and feature-generation history.
- Universe membership provenance, point-in-time inclusion, delistings, repeated symbols, and exclusions. Do not claim survivorship-free or broad-market coverage without evidence.

### D. Fixture ruling — explicit required answer

The existing records disclose a prior development-suite test read **only the header/schema of a staged development event-table fixture**; no event rows were consumed for analysis, fitting, or scoring. Please rule explicitly whether that exact metadata-only operation was within the authorized boundary, citing the controlling permission. Options: `PERMITTED AS DOCUMENTED`, `OUT OF SCOPE / INCIDENT`, or `NOT DETERMINABLE`. Do not infer permission solely from `FIXTURE_PROVENANCE.json` labeling it a development fixture.

Also decide future fixture policy: which synthetic fixtures may be created and used; whether any real-data-derived copy, schema/header, labels, IDs, hashes, aggregates, or counts are allowed; permitted root and access controls; and whether future suites must be strictly synthetic. If an incident is found, state containment/notification/recordkeeping steps without expanding access.

### E. Outputs, monitoring, and reviewer disposition

Define allowed output classes and recipients, whether counts/hashes/aggregate metrics may leave an isolated run, and prohibited outputs. Provide non-content evidence of boundary isolation and auditable access logging. The independent reviewer must assess the boundary, exposure and dependence claims and may mark any point `NOT DETERMINABLE`; reviewer acceptance is not owner permission.

## Required closure statement

Conclude one of:

- `BOUNDARY ESTABLISHED FOR REVIEW ONLY` — exact scope and restrictions above, no execution permission; or
- `NOT DETERMINABLE — KEEP BLOCKED`; or
- `PROPOSED SOURCE/OPERATION REJECTED`.

This ruling can enable the independent reviewer to assess a draft. It does not choose a protocol, freeze a predeclaration, grant data use, or authorize any Campaign 5 operation. Separate exact owner authorization remains required after all prerequisites. No campaign, evaluation, fitting, scoring, holdout access, candidate activation, integration, or launch is permitted by this request.
