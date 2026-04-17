# TrailForge Static Delivery Acceptance + Architecture Audit
Date: 2026-04-04
Mode: Static-only (no runtime execution)

## 1. Verdict
- Overall conclusion: **Fail**
- Primary reason: Blocker-level production-path defect in PostgreSQL retention/restore lifecycle (immutable trigger conflict), plus major audit trail coverage gap for sensitive permission changes.

## 2. Scope and Static Verification Boundary
- Reviewed:
  - Documentation and manifests (`repo/README.md`, `repo/docker-compose.yml`, `repo/run_tests.sh`, ops docs)
  - Backend architecture, routes, services, schemas, models, migrations
  - Frontend workspace/router/store/API/static UI structure
  - Backend/frontend/e2e tests and test configs (static read only)
- Not reviewed:
  - External infra and host-level TLS trust setup
  - Runtime behavior under real network latency/concurrency
- Intentionally not executed:
  - Project startup, Docker, test suites, migrations, browsers, external services
- Manual verification required for:
  - Runtime HTTPS cert trust/user browser behavior (`repo/ops/certs/README.md:1`)
  - Actual UI rendering/interaction fidelity in browser beyond static component code
  - End-to-end behavior in true PostgreSQL runtime (critical given SQLite-heavy test path)

## 3. Repository / Requirement Mapping Summary
- Prompt core goal mapped: offline-first itinerary management with governed data, secure collaboration, controlled media handling, sync packaging, message center caps, RBAC, audit/lineage, retention, encrypted backups/restore.
- Main implementation areas reviewed:
  - Auth/session/token/CSRF: `repo/backend/app/api/routes/auth.py`, `repo/backend/app/api/deps.py`, `repo/backend/app/services/auth.py`
  - Governance/RBAC/planner/resource/message/ops routes and services: `repo/backend/app/api/routes/*.py`, `repo/backend/app/services/*.py`
  - Data model + migration guarantees: `repo/backend/app/models/*.py`, `repo/backend/alembic/versions/*.py`
  - Frontend workspace flows: `repo/frontend/src/views/*.vue`, router/store/api modules
  - Tests: `repo/backend/tests/*.py`, `repo/frontend/tests/**/*`

## 4. Section-by-section Review

### 1. Hard Gates

#### 1.1 Documentation and static verifiability
- Conclusion: **Pass**
- Rationale: Startup/test/config surfaces are documented and statically align with code layout and route registration.
- Evidence:
  - Startup/test commands and runtime notes: `repo/README.md:147`, `repo/README.md:151`, `repo/README.md:155`, `repo/README.md:163`
  - Route inventory documented: `repo/README.md:36`, `repo/README.md:48`, `repo/README.md:63`
  - Entry-point wiring: `repo/backend/app/main.py:22`, `repo/backend/app/api/routes/__init__.py:12`
  - Compose service topology: `repo/docker-compose.yml:32`, `repo/docker-compose.yml:68`, `repo/docker-compose.yml:94`
- Manual verification note: Runtime startup success is not claimed.

#### 1.2 Material deviation from Prompt
- Conclusion: **Partial Pass**
- Rationale: System largely aligns with prompt flows, but two material deviations remain: PostgreSQL retention/restore blocker and incomplete sensitive-action audit coverage (permission changes).
- Evidence:
  - Prompt-aligned features (planner/sync/resource/message/ops) implemented in backend/frontend: `repo/README.md:22`, `repo/README.md:24`, `repo/README.md:25`, `repo/README.md:26`, `repo/README.md:30`
  - Material deviations evidenced under Issues #1 and #2.

### 2. Delivery Completeness

#### 2.1 Core explicit requirements coverage
- Conclusion: **Partial Pass**
- Rationale: Most explicit functional requirements are implemented; critical operations path for retention/restore on PostgreSQL is statically broken.
- Evidence:
  - Planner distance/time + warnings: `repo/backend/app/services/planner.py:327`, `repo/backend/app/services/planner.py:353`, `repo/backend/app/services/planner.py:368`
  - Import/export + receipts: `repo/backend/app/services/planner.py:622`, `repo/backend/app/services/planner.py:698`, `repo/frontend/src/views/WorkspacePlannerView.vue:1236`
  - Sync package integrity/conflict receipts: `repo/backend/app/services/planner.py:1949`, `repo/backend/app/services/planner.py:2155`, `repo/frontend/src/views/WorkspacePlannerView.vue:888`
  - Resource-center controls: `repo/backend/app/services/resource_center.py:23`, `repo/backend/app/services/resource_center.py:146`, `repo/backend/app/services/resource_center.py:236`
  - Message center caps/connectors: `repo/backend/app/services/message_center.py:28`, `repo/backend/app/services/message_center.py:366`, `repo/backend/app/services/message_delivery.py:65`
  - Retention/backup/restore target features: `repo/backend/app/services/operations.py:291`, `repo/backend/app/services/operations.py:430`, `repo/backend/scripts/operations_daemon.py:27`
  - Blocker conflict for PostgreSQL immutable tables: `repo/backend/alembic/versions/0007_audit_ops_foundations.py:162`, `repo/backend/app/services/operations.py:603`, `repo/backend/app/services/operations.py:238`

#### 2.2 End-to-end 0→1 deliverable vs partial/demo
- Conclusion: **Pass**
- Rationale: Multi-module backend/frontend plus migrations/docs/tests are present; not a toy fragment.
- Evidence:
  - Full stack layout: `repo/backend`, `repo/frontend`, `repo/ops`
  - README and operator docs: `repo/README.md:1`, `repo/ops/backups/README.md:1`
  - API route breadth: `repo/backend/tests/route_test_matrix.md:5`

### 3. Engineering and Architecture Quality

#### 3.1 Structure and module decomposition
- Conclusion: **Pass**
- Rationale: Clear separation of routes/services/models/schemas/tests and corresponding frontend modules.
- Evidence:
  - Backend decomposition: `repo/backend/app/api/routes/__init__.py:12`, `repo/backend/app/services/planner.py:1`, `repo/backend/app/models/planner.py:16`
  - Frontend decomposition: `repo/frontend/src/router/index.ts:48`, `repo/frontend/src/stores/auth.ts:21`, `repo/frontend/src/views/WorkspacePlannerView.vue:1`

#### 3.2 Maintainability/extensibility
- Conclusion: **Partial Pass**
- Rationale: Strong baseline patterns, but key maintainability/security risks remain (missing sensitive-action audit hooks; PostgreSQL parity gap in operations lifecycle).
- Evidence:
  - Extensible abstractions present (object storage, connectors): `repo/backend/app/services/object_storage.py:18`, `repo/backend/app/services/message_delivery.py:26`
  - Gaps evidenced in Issues #1/#2.

### 4. Engineering Details and Professionalism

#### 4.1 Error handling, logging, validation, API design
- Conclusion: **Partial Pass**
- Rationale: Validation and HTTP error mapping are generally robust, but logging/audit protections are incomplete in coverage and test assurance.
- Evidence:
  - Validation/range checks: `repo/backend/app/schemas/governance.py:93`, `repo/backend/app/schemas/planner.py:67`, `repo/backend/app/services/resource_center.py:236`
  - Error mapping patterns: `repo/backend/app/api/routes/planner.py:583`, `repo/backend/app/api/routes/resource_center.py:87`
  - Redaction logic exists but test evidence is weak: `repo/backend/app/core/logging.py:5`, `repo/backend/app/services/audit.py:11`

#### 4.2 Product-like service vs demo
- Conclusion: **Pass**
- Rationale: Delivery includes governance/planner/resources/messages/operations modules with persisted models, migrations, and route test matrix.
- Evidence:
  - Feature breadth in README and code: `repo/README.md:22`, `repo/README.md:30`, `repo/backend/tests/route_test_matrix.md:78`

### 5. Prompt Understanding and Requirement Fit

#### 5.1 Business goal and constraints fit
- Conclusion: **Partial Pass**
- Rationale: Core business flows are implemented with strong prompt alignment, but security/compliance-critical defects prevent full acceptance.
- Evidence:
  - Offline-oriented connector behavior and sync package: `repo/backend/app/services/message_delivery.py:48`, `repo/backend/app/services/planner.py:1618`
  - Required step-up model: `repo/backend/app/core/config.py:31`, `repo/backend/app/api/routes/governance.py:478`, `repo/backend/app/api/routes/governance.py:516`
  - Failing requirements reflected by Issues #1/#2.

### 6. Aesthetics (frontend-only)

#### 6.1 Visual and interaction quality fit
- Conclusion: **Cannot Confirm Statistically**
- Rationale: Static Vue/CSS indicates structured panels, save-state, warnings, drag-drop, and progress cues, but visual rendering quality and interaction polish require browser verification.
- Evidence:
  - Interaction/feedback hooks: `repo/frontend/src/views/WorkspacePlannerView.vue:1093`, `repo/frontend/src/views/WorkspacePlannerView.vue:1105`, `repo/frontend/src/views/WorkspacePlannerView.vue:1158`, `repo/frontend/src/views/WorkspacePlannerView.vue:969`
  - Global styling baseline: `repo/frontend/src/styles.css:1`
- Manual verification note: Browser walkthrough required for final UX quality sign-off.

## 5. Issues / Suggestions (Severity-Rated)

### Blocker

#### 1) PostgreSQL retention/restore path conflicts with immutable audit/lineage triggers
- Severity: **Blocker**
- Conclusion: **Fail**
- Evidence:
  - PostgreSQL immutable triggers forbid DELETE on `audit_events`/`lineage_events`: `repo/backend/alembic/versions/0007_audit_ops_foundations.py:162`, `repo/backend/alembic/versions/0007_audit_ops_foundations.py:169`
  - Retention deletes audit/lineage rows without PostgreSQL trigger disable path: `repo/backend/app/services/operations.py:571`, `repo/backend/app/services/operations.py:603`, `repo/backend/app/services/operations.py:613`
  - Restore only drops immutable triggers for SQLite, not PostgreSQL: `repo/backend/app/services/operations.py:229`, `repo/backend/app/services/operations.py:234`, `repo/backend/app/services/operations.py:238`
  - Backups include audit/lineage tables (not excluded), so restore touches those tables: `repo/backend/app/services/operations.py:25`, `repo/backend/app/services/operations.py:172`, `repo/backend/app/services/operations.py:173`
- Impact:
  - In PostgreSQL runtime, retention and restore can fail when org has immutable-event rows; nightly lifecycle objectives and documented restore path are not reliably deliverable.
- Minimum actionable fix:
  - Implement PostgreSQL-safe immutable lifecycle strategy (for example controlled trigger disable/enable or partitioned archival process) for retention/restore operations.
  - Add explicit PostgreSQL integration tests for retention + restore with populated audit/lineage rows.

### High

#### 2) Sensitive permission changes are not audit-logged
- Severity: **High**
- Conclusion: **Fail**
- Evidence:
  - Permission-change endpoints exist and require step-up: `repo/backend/app/api/routes/governance.py:474`, `repo/backend/app/api/routes/governance.py:511`, `repo/backend/app/api/routes/governance.py:542`
  - These handlers do not call `record_audit_event` in their bodies.
  - Only attraction merge in governance is explicitly audited: `repo/backend/app/api/routes/governance.py:303`
- Impact:
  - Immutable audit trail is incomplete for sensitive authorization state mutations (`role_in_project`, `can_edit`), weakening compliance and forensic traceability.
- Minimum actionable fix:
  - Add audit events for project-member create/update/delete and other governance write actions deemed sensitive.
  - Add tests asserting these audit events are persisted with actor/resource metadata.

#### 3) Default compose runtime disables secure session cookies
- Severity: **High**
- Conclusion: **Partial Fail**
- Evidence:
  - Compose sets `TF_SESSION_COOKIE_SECURE: "false"`: `repo/docker-compose.yml:48`, `repo/docker-compose.yml:139`
  - Auth cookie security flag follows this setting: `repo/backend/app/api/routes/auth.py:45`, `repo/backend/app/api/routes/auth.py:54`
- Impact:
  - Session/CSRF cookies can be transmitted over non-HTTPS contexts if exposed, conflicting with the intended secure local-network HTTPS posture.
- Minimum actionable fix:
  - Set secure cookies to true in production-like compose profile and document any local-only exception profile separately.

### Medium

#### 4) Message frequency caps are non-atomic and race-prone
- Severity: **Medium**
- Conclusion: **Partial Fail**
- Evidence:
  - Caps are checked via count queries: `repo/backend/app/services/message_center.py:377`, `repo/backend/app/services/message_center.py:393`
  - Insert happens afterward in separate statements without lock/unique constraint: `repo/backend/app/services/message_center.py:480`, `repo/backend/app/services/message_center.py:527`
- Impact:
  - Concurrent sends can bypass 3/day and 1/hour caps.
- Minimum actionable fix:
  - Enforce caps with transactional locking or durable quota table + unique constraints per bucket.

#### 5) Test environment defaults to SQLite, leaving PostgreSQL-specific failures undetected
- Severity: **Medium**
- Conclusion: **Partial Fail**
- Evidence:
  - Tests auto-fallback to SQLite when Docker DB vars absent: `repo/backend/tests/conftest.py:34`, `repo/backend/tests/conftest.py:35`, `repo/backend/tests/conftest.py:66`
  - SQLite has dedicated trigger-drop workaround not mirrored for PostgreSQL lifecycle paths: `repo/backend/app/services/operations.py:79`, `repo/backend/app/services/operations.py:229`
- Impact:
  - Critical production-path defects (Issue #1) can pass CI/static review unnoticed.
- Minimum actionable fix:
  - Add mandatory PostgreSQL-mode operations tests in CI for retention/restore with immutable-event fixtures.

#### 6) Sensitive log-redaction behavior lacks direct automated verification
- Severity: **Medium**
- Conclusion: **Partial Fail**
- Evidence:
  - Redaction implementations exist: `repo/backend/app/core/logging.py:5`, `repo/backend/app/services/audit.py:24`
  - No dedicated backend tests target these redaction paths (static test scan found no `RedactionFilter`/`_redact` assertions).
- Impact:
  - Regressions could expose sensitive values in logs/audit metadata without failing tests.
- Minimum actionable fix:
  - Add unit tests for regex filter redaction and recursive metadata key redaction.

### Low

#### 7) Source tree contains generated JS artifacts parallel to TS sources
- Severity: **Low**
- Conclusion: **Maintainability Risk**
- Evidence:
  - Duplicate TS/JS source pairs: `repo/frontend/src/api/client.ts`, `repo/frontend/src/api/client.js`, `repo/frontend/src/router/index.ts`, `repo/frontend/src/router/index.js`
  - Duplicate TS/JS test pairs: `repo/frontend/tests/unit/api-client.spec.ts`, `repo/frontend/tests/unit/api-client.spec.js`
- Impact:
  - Drift/confusion risk in maintenance and review.
- Minimum actionable fix:
  - Exclude generated JS/maps from source tree or enforce single-source-of-truth policy.

## 6. Security Review Summary

- Authentication entry points: **Pass**
  - Evidence: credential auth, session issuance, token lifecycle, step-up path: `repo/backend/app/api/routes/auth.py:30`, `repo/backend/app/api/routes/auth.py:80`, `repo/backend/app/api/routes/auth.py:93`
- Route-level authorization: **Pass**
  - Evidence: role dependencies and route guards: `repo/backend/app/api/deps.py:61`, `repo/backend/app/api/deps.py:90`, `repo/backend/app/api/routes/operations.py:126`
- Object-level authorization: **Pass**
  - Evidence: org/project/assignment checks in planner/resource/message services: `repo/backend/app/services/planner.py:264`, `repo/backend/app/services/resource_center.py:72`, `repo/backend/app/services/message_center.py:60`
- Function-level authorization: **Partial Pass**
  - Evidence: step-up gates present for sensitive actions: `repo/backend/app/api/deps.py:45`, `repo/backend/app/api/routes/governance.py:478`, `repo/backend/app/api/routes/governance.py:249`
  - Gap: sensitive permission changes are not audit-logged (Issue #2).
- Tenant/user data isolation: **Pass**
  - Evidence: org-scoped queries and restore scope enforcement: `repo/backend/app/services/planner.py:264`, `repo/backend/app/services/operations.py:210`, `repo/backend/tests/test_operations.py:536`
- Admin/internal/debug endpoint protection: **Pass**
  - Evidence: ops mutation routes require ORG_ADMIN+CSRF(+step-up where needed): `repo/backend/app/api/routes/operations.py:139`, `repo/backend/app/api/routes/operations.py:265`
  - Note: health endpoints are intentionally public (`repo/backend/app/api/routes/health.py:10`).

## 7. Tests and Logging Review

- Unit tests: **Partial Pass**
  - Backend and frontend unit-style tests exist (`pytest`, `vitest`), covering many validation/auth paths.
  - Evidence: `repo/backend/pytest.ini:1`, `repo/frontend/vitest.config.ts:4`, `repo/frontend/tests/unit/router-access.spec.ts:27`
- API/integration tests: **Partial Pass**
  - Broad API route coverage and E2E suite exist, but backend defaults to SQLite and E2E can skip on missing creds.
  - Evidence: `repo/backend/tests/route_test_matrix.md:78`, `repo/backend/tests/conftest.py:34`, `repo/frontend/tests/e2e/planner-core.spec.ts:7`
- Logging categories/observability: **Partial Pass**
  - Basic logging exists for app/ops-daemon; audit/lineage event models provide observability surfaces.
  - Evidence: `repo/backend/app/core/logging.py:15`, `repo/backend/scripts/operations_daemon.py:12`, `repo/backend/app/models/operations.py:18`
- Sensitive-data leakage risk in logs/responses: **Partial Pass**
  - Mitigations exist (redaction filter + key-based metadata redaction), but automated regression checks are missing.
  - Evidence: `repo/backend/app/core/logging.py:5`, `repo/backend/app/services/audit.py:11`

## 8. Test Coverage Assessment (Static Audit)

### 8.1 Test Overview
- Unit/API/integration tests exist:
  - Backend: `pytest` (`repo/backend/pytest.ini:1`)
  - Frontend unit: `vitest` (`repo/frontend/vitest.config.ts:4`)
  - Frontend E2E: `playwright` (`repo/frontend/playwright.config.ts:3`)
- Test entry points documented:
  - Full suite command: `repo/README.md:155`
  - Backend local pytest command: `repo/README.md:165`
- Route-test mapping artifact exists:
  - `repo/backend/tests/route_test_matrix.md:1`

### 8.2 Coverage Mapping Table

| Requirement / Risk Point | Mapped Test Case(s) | Key Assertion / Fixture / Mock | Coverage Assessment | Gap | Minimum Test Addition |
|---|---|---|---|---|---|
| Auth login/session/`/me` | `repo/backend/tests/test_auth.py:1` | login 200 + `/me` org/user assertions `repo/backend/tests/test_auth.py:11` | basically covered | No brute-force/rate-limit checks | Add auth abuse/rate-limit tests (if feature intended) |
| CSRF enforcement on mutating auth endpoints | `repo/backend/tests/test_auth.py:40` | missing CSRF returns 403 `repo/backend/tests/test_auth.py:51` | sufficient | Coverage focused on auth routes | Add CSRF-negative cases for key governance/planner mutations |
| Step-up window enforcement for sensitive actions | `repo/backend/tests/test_governance.py:344`, `repo/backend/tests/test_governance.py:391` | 403 without step-up and 200 after step-up | sufficient | No expiry-boundary test at ~10 min | Add boundary-time test around `step_up_window_minutes` |
| RBAC route-level restrictions (admin/planner/auditor) | `repo/backend/tests/test_governance.py:59`, `repo/backend/tests/test_operations.py:471`, `repo/backend/tests/test_operations.py:502` | 403 for forbidden role paths | sufficient | None major | Add matrix test for every mutation route 403 behavior |
| Tenant isolation (cross-org block) | `repo/backend/tests/test_governance.py:76`, `repo/backend/tests/test_planner.py:250`, `repo/backend/tests/test_operations.py:518` | 404/422 cross-org blocking assertions | sufficient | None major | Keep as regression suite |
| Planner warnings (overlap 15m, >12h), versioning, reorder | `repo/backend/tests/test_planner.py:85`, `repo/frontend/tests/e2e/planner-core.spec.ts:5` | warning codes + reorder/version checks | sufficient | No concurrency/race test for reorder writes | Add concurrent reorder conflict test |
| CSV/XLSX import-export + readable receipt | `repo/backend/tests/test_planner.py:277`, `repo/backend/tests/test_planner.py:315`, `repo/backend/tests/test_planner.py:360` | content-type and receipt accepted/rejected/hints checks | sufficient | None major | Add malformed-header + extreme row-volume tests |
| Sync package integrity/conflict/token auth | `repo/backend/tests/test_planner.py:457`, `repo/backend/tests/test_planner.py:518`, `repo/backend/tests/test_planner.py:567` | checksum mismatch + conflict + bearer token flows | sufficient | No concurrent sync-import race tests | Add concurrent imports against same itinerary/version |
| Resource center validation controls + cleanup | `repo/backend/tests/test_resource_center.py:128`, `repo/backend/tests/test_resource_center.py:142`, `repo/backend/tests/test_resource_center.py:191` | extension/MIME mismatch, size cap, cleanup delete eligibility | sufficient | No tests for dangerous filename/header edge cases | Add filename sanitization/header injection test |
| Message center variable render + caps + offline connectors | `repo/backend/tests/test_message_center.py:74` | hourly/daily cap assertions, sms offline failure | basically covered | No concurrency cap-bypass tests | Add concurrent send tests for cap enforcement |
| Ops backup/restore/retention/audit/lineage | `repo/backend/tests/test_operations.py:69`, `repo/backend/tests/test_operations.py:365` | backup/restore success, immutable behavior (SQLite path) | insufficient | PostgreSQL-specific immutable-trigger behavior not covered | Add PostgreSQL integration tests for retention/restore with non-empty audit/lineage |
| Sensitive-action audit logging (permission changes) | none for project-member audit entries | N/A | missing | No test asserts audit rows for member create/update/delete | Add governance audit-assert tests for permission changes |
| Log redaction / sensitive leak prevention | none targeting logger/audit redaction internals | N/A | missing | Redaction regressions undetected | Add unit tests for `RedactionFilter` and audit `_redact` |

### 8.3 Security Coverage Audit
- Authentication: **Basically covered**
  - Login/me/step-up/token lifecycle tests exist (`repo/backend/tests/test_auth.py:1`, `repo/backend/tests/test_auth.py:55`).
- Route authorization: **Covered**
  - Role denial/allow patterns tested across governance/ops (`repo/backend/tests/test_governance.py:59`, `repo/backend/tests/test_operations.py:471`).
- Object-level authorization: **Covered**
  - Cross-org and project scoping tests exist (`repo/backend/tests/test_planner.py:185`, `repo/backend/tests/test_planner.py:250`).
- Tenant/data isolation: **Covered**
  - Cross-org restore and data separation tested (`repo/backend/tests/test_operations.py:536`).
- Admin/internal protection: **Covered**
  - Auditor read-only vs mutation denial validated (`repo/backend/tests/test_operations.py:498`).
- Residual severe blind spots:
  - No PostgreSQL-path tests for immutable trigger interaction (critical).
  - No tests proving audit emission for permission-change endpoints.

### 8.4 Final Coverage Judgment
- **Fail**
- Boundary explanation:
  - Major happy paths and many security controls are tested.
  - Uncovered high-risk areas (PostgreSQL immutable-trigger lifecycle, sensitive-action audit completeness, redaction regression tests) mean tests can pass while severe production defects remain.

## 9. Final Notes
- This audit is static-only and evidence-bound.
- Runtime behavior was not claimed without code/test proof.
- Root-cause issues were prioritized over repetitive symptoms.


