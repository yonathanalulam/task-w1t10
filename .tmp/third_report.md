# TrailForge Static Delivery Acceptance + Architecture Audit

## 1. Verdict
- **Overall conclusion: Fail**
- Core business functionality is largely implemented and test-backed, but a high-severity security hardening regression exists in the delivered runtime configuration (`TF_SESSION_COOKIE_SECURE=false`), conflicting with the Prompt’s HTTPS/browser-session security intent.

## 2. Scope and Static Verification Boundary
- **Reviewed (static only):**
  - Documentation, startup/config/test instructions: `README.md`, `docker-compose.yml`, `run_tests.sh`, `ops/backups/README.md`
  - Backend architecture/security/business logic: `backend/app/**`, `backend/alembic/**`, `backend/scripts/**`
  - Frontend architecture/workspace/API contracts: `frontend/src/**`
  - Test suites and config (read only): `backend/tests/**`, `frontend/tests/**`, `backend/pytest.ini`, `frontend/package.json`
- **Not reviewed/executed:** runtime behavior under real startup, browser interaction timing, network/cert trust chain behavior, Docker orchestration behavior under load.
- **Intentionally not executed:** project startup, Docker commands, test runs, external services.
- **Manual verification required for claims depending on runtime:**
  - TLS/certificate trust and end-to-end HTTPS enforcement at runtime
  - Drag-and-drop smoothness, autosave timing UX, and client rendering fidelity
  - Time-driven daemon behavior (nightly schedule and periodic cleanup timing)

## 3. Repository / Requirement Mapping Summary
- **Prompt core goal mapped:** offline-first itinerary operations with secure local auth, RBAC, governed catalog/planner/import/export/sync, controlled assets, message center caps, and auditable operations.
- **Main implementation areas mapped:**
  - Governance/RBAC: `backend/app/api/routes/governance.py`, `backend/app/services/governance.py`
  - Planner/import/export/sync: `backend/app/services/planner.py`, `frontend/src/views/WorkspacePlannerView.vue`
  - Resource center: `backend/app/services/resource_center.py`, `backend/app/models/resource_center.py`
  - Message center: `backend/app/services/message_center.py`, `backend/app/services/message_delivery.py`
  - Ops/audit/lineage/backup/restore/retention: `backend/app/api/routes/operations.py`, `backend/app/services/operations.py`, `backend/alembic/versions/0007_audit_ops_foundations.py`
  - Auth/session/token/CSRF: `backend/app/api/deps.py`, `backend/app/api/routes/auth.py`, `backend/app/services/auth.py`

## 4. Section-by-section Review

### 1. Hard Gates
- **1.1 Documentation and static verifiability**
  - **Conclusion:** Partial Pass
  - **Rationale:** Startup/config/test instructions and endpoint surfaces are documented and generally align statically with entrypoints; however, one runtime security setting in Compose conflicts with secure HTTPS cookie intent.
  - **Evidence:** `README.md:7`, `README.md:36`, `README.md:90`, `README.md:147`, `docker-compose.yml:32`, `docker-compose.yml:48`, `backend/scripts/entrypoint.sh:20`, `backend/pytest.ini:1`
  - **Manual verification note:** Runtime startup and cert behavior were not executed.
- **1.2 Material deviation from Prompt**
  - **Conclusion:** Partial Pass
  - **Rationale:** Core workflows match Prompt well, but delivered cookie security configuration weakens required secure browser-session posture.
  - **Evidence:** `docker-compose.yml:48`, `backend/app/core/config.py:29`, `backend/app/api/routes/auth.py:45`

### 2. Delivery Completeness
- **2.1 Core explicit requirements coverage**
  - **Conclusion:** Partial Pass
  - **Rationale:** Most explicit features are implemented (planner warnings/calculations, CSV/XLSX import/export receipts, sync package integrity/conflict handling, asset validation+cleanup, message caps, RBAC, audit/lineage, retention/backup/restore). Two material gaps remain: operations frontend contract drift and incomplete automatic cleanup coverage for all unreferenced-asset paths.
  - **Evidence:** `backend/app/services/planner.py:327`, `backend/app/services/planner.py:698`, `backend/app/services/planner.py:1676`, `backend/app/services/planner.py:1948`, `backend/app/services/resource_center.py:220`, `backend/app/services/message_center.py:367`, `backend/app/services/operations.py:594`, `backend/app/schemas/operations.py:40`, `frontend/src/api/operations.ts:3`
- **2.2 End-to-end 0→1 deliverable (not a demo fragment)**
  - **Conclusion:** Pass
  - **Rationale:** Full backend/frontend/project structure, migrations, scripts, and substantial automated tests exist.
  - **Evidence:** `backend/app/main.py:22`, `backend/alembic/versions/0007_audit_ops_foundations.py:21`, `frontend/src/router/index.ts:48`, `backend/tests/route_test_matrix.md:78`, `README.md:138`

### 3. Engineering and Architecture Quality
- **3.1 Structure/module decomposition**
  - **Conclusion:** Pass
  - **Rationale:** Clear separation by domain (auth/governance/planner/resource/message/operations), with route-service-model-schema layering.
  - **Evidence:** `backend/app/api/routes/__init__.py:12`, `backend/app/services/planner.py:622`, `backend/app/services/resource_center.py:220`, `backend/app/services/message_center.py:367`, `backend/app/services/operations.py:543`
- **3.2 Maintainability/extensibility**
  - **Conclusion:** Partial Pass
  - **Rationale:** Generally extensible (object storage abstraction, connector registry, schema-based APIs), but frontend/backend operations API contract drift indicates maintainability risk.
  - **Evidence:** `backend/app/services/object_storage.py:18`, `backend/app/services/message_delivery.py:65`, `backend/app/schemas/operations.py:51`, `frontend/src/api/operations.ts:12`

### 4. Engineering Details and Professionalism
- **4.1 Error handling/logging/validation/API detail quality**
  - **Conclusion:** Partial Pass
  - **Rationale:** Strong validation and structured HTTP errors are present; sensitive metadata/log redaction exists. High-severity cookie hardening regression remains.
  - **Evidence:** `backend/app/api/deps.py:65`, `backend/app/services/resource_center.py:224`, `backend/app/services/message_center.py:390`, `backend/app/services/audit.py:24`, `backend/app/core/logging.py:5`, `docker-compose.yml:48`
- **4.2 Product-like delivery vs demo**
  - **Conclusion:** Pass
  - **Rationale:** Includes operational concerns (retention, backup, restore, audit, lineage), not just demo CRUD.
  - **Evidence:** `backend/app/api/routes/operations.py:126`, `backend/app/services/operations.py:317`, `ops/backups/README.md:42`

### 5. Prompt Understanding and Requirement Fit
- **5.1 Business goal and constraints fit**
  - **Conclusion:** Partial Pass
  - **Rationale:** Business scenario is implemented with appropriate offline connector behavior and governance/planner flow. Security hardening mismatch (secure cookies disabled in delivered Compose runtime) weakens Prompt-fit.
  - **Evidence:** `backend/app/services/message_delivery.py:48`, `backend/app/services/planner.py:349`, `backend/app/services/governance.py:399`, `docker-compose.yml:48`

### 6. Aesthetics (frontend)
- **6.1 Visual/interaction quality**
  - **Conclusion:** Cannot Confirm Statistically
  - **Rationale:** Static code shows module separation, feedback surfaces, and stateful UI elements, but final visual quality and interaction behavior require runtime/browser validation.
  - **Evidence:** `frontend/src/views/WorkspacePlannerView.vue:1236`, `frontend/src/views/WorkspacePlannerView.vue:888`, `frontend/src/views/WorkspaceOperationsView.vue:195`, `frontend/src/components/WorkspaceShell.vue:31`
  - **Manual verification note:** Requires interactive browser review.

## 5. Issues / Suggestions (Severity-Rated)

### 1) High — Session cookies are explicitly configured insecure in delivered HTTPS Compose runtime
- **Conclusion:** Fail
- **Evidence:** `docker-compose.yml:48`, `backend/app/core/config.py:29`, `backend/app/api/routes/auth.py:45`
- **Impact:** Browser session/CSRF cookies are set without `Secure` in the primary Compose runtime despite HTTPS claims, weakening transport-level session protection.
- **Minimum actionable fix:** Set `TF_SESSION_COOKIE_SECURE: "true"` for the `backend` service in Compose (keep insecure only in isolated test profiles if needed), and document environment-specific rationale.

### 2) High — Automatic unreferenced-file cleanup misses retention/cascade orphaning path
- **Conclusion:** Fail
- **Evidence:** `backend/app/models/resource_center.py:38`, `backend/app/models/resource_center.py:39`, `backend/app/services/operations.py:616`, `backend/app/services/resource_center.py:510`, `backend/app/services/resource_center.py:526`
- **Impact:** Prompt requires unreferenced files be automatically cleaned after 30 days. Current cleanup logic only deletes assets with non-null `cleanup_eligible_at`, but that timestamp is only set by explicit asset unreference endpoint; assets orphaned indirectly (for example after itinerary deletion during retention) can remain indefinitely.
- **Minimum actionable fix:** Add a periodic sweeper step that stamps `cleanup_eligible_at` for any asset where `attraction_id IS NULL AND itinerary_id IS NULL AND cleanup_eligible_at IS NULL`, or enforce this with DB trigger/application hooks when FK nulling occurs.

### 3) Medium — Frontend operations API contract is out-of-sync with backend retention response models
- **Conclusion:** Partial Fail
- **Evidence:** `backend/app/schemas/operations.py:40`, `backend/app/schemas/operations.py:57`, `frontend/src/api/operations.ts:3`, `frontend/src/api/operations.ts:12`, `frontend/src/views/WorkspaceOperationsView.vue:236`
- **Impact:** Operations UI/type layer omits audit/lineage retention fields and deletion counts, reducing operator visibility for retention compliance outcomes and increasing drift risk.
- **Minimum actionable fix:** Update frontend `RetentionPolicy`/`RetentionRun` types and Operations UI rendering to include `audit_retention_days`, `lineage_retention_days`, `deleted_audit_event_count`, and `deleted_lineage_event_count`.

## 6. Security Review Summary
- **Authentication entry points:** **Partial Pass**
  - Evidence: `backend/app/api/routes/auth.py:30`, `backend/app/api/routes/auth.py:93`, `backend/app/api/deps.py:22`, `docker-compose.yml:48`
  - Reasoning: Login/session/step-up/API-token flows exist with hashing/encryption, but secure cookie hardening is disabled in Compose runtime.
- **Route-level authorization:** **Pass**
  - Evidence: `backend/app/api/deps.py:61`, `backend/app/api/deps.py:90`, `backend/app/api/routes/governance.py:124`, `backend/app/api/routes/operations.py:126`
  - Reasoning: Role-gated dependencies are consistently applied.
- **Object-level authorization:** **Pass**
  - Evidence: `backend/app/services/planner.py:252`, `backend/app/services/resource_center.py:451`, `backend/app/services/message_center.py:61`
  - Reasoning: Resource access is constrained by org/project membership and assignment guards.
- **Function-level authorization (sensitive operations):** **Pass**
  - Evidence: `backend/app/api/routes/governance.py:267`, `backend/app/api/routes/governance.py:496`, `backend/app/api/routes/operations.py:135`, `backend/app/api/routes/operations.py:261`, `backend/app/core/config.py:31`
  - Reasoning: Step-up gate is enforced for permission changes, merges, retention-policy updates, and restore.
- **Tenant / user data isolation:** **Pass**
  - Evidence: `backend/app/services/planner.py:264`, `backend/app/services/operations.py:247`, `backend/tests/test_operations.py:639`
  - Reasoning: Org scoping is enforced in query filters and backup restore scope checks.
- **Admin / internal / debug protection:** **Pass**
  - Evidence: `backend/app/api/routes/governance.py:107`, `backend/app/api/routes/governance.py:109`, `backend/app/api/routes/operations.py:197`, `backend/app/api/routes/health.py:1`
  - Reasoning: Admin/internal data routes are role-guarded; health endpoints are intentionally public.

## 7. Tests and Logging Review
- **Unit tests:** Pass
  - Evidence: `backend/tests/test_auth.py:1`, `backend/tests/test_logging.py:13`, `frontend/tests/unit/router-access.spec.ts:5`, `frontend/package.json:10`
- **API / integration tests:** Pass
  - Evidence: `backend/tests/test_planner.py:85`, `backend/tests/test_resource_center.py:128`, `backend/tests/test_operations.py:69`, `backend/tests/route_test_matrix.md:78`, `frontend/tests/e2e/planner-core.spec.ts:5`, `frontend/tests/e2e/message-center.spec.ts:25`
- **Logging categories / observability:** Partial Pass
  - Evidence: `backend/app/core/logging.py:15`, `backend/app/services/audit.py:38`, `backend/app/services/operations.py:643`
  - Reasoning: Useful audit/lineage/run-history observability exists; global logger setup is basic.
- **Sensitive-data leakage risk in logs/responses:** Partial Pass
  - Evidence: `backend/app/core/logging.py:5`, `backend/app/services/audit.py:11`, `backend/tests/test_logging.py:13`
  - Reasoning: Redaction exists and is tested; runtime behavior across all third-party log emissions still requires manual/runtime confirmation.

## 8. Test Coverage Assessment (Static Audit)

### 8.1 Test Overview
- **Unit/API/integration tests exist:** yes (backend `pytest`, frontend `vitest`, frontend `playwright`).
- **Frameworks and entry points:**
  - Backend: `pytest` (`backend/requirements-dev.txt:1`, `backend/pytest.ini:1`)
  - Frontend unit: `vitest` (`frontend/package.json:10`)
  - Frontend e2e: `playwright` (`frontend/package.json:11`)
- **Documentation provides test commands:** yes (`README.md:155`, `README.md:163`, `README.md:167`).

### 8.2 Coverage Mapping Table
| Requirement / Risk Point | Mapped Test Case(s) | Key Assertion / Fixture / Mock | Coverage Assessment | Gap | Minimum Test Addition |
|---|---|---|---|---|---|
| Login/session/CSRF enforcement | `backend/tests/test_auth.py:1`, `backend/tests/test_auth.py:40` | Missing CSRF rejected `403` (`backend/tests/test_auth.py:51`) | sufficient | No test for cookie `Secure` flag config | Add API-level assertion on `Set-Cookie` includes `Secure` in non-test runtime config |
| Step-up for sensitive actions | `backend/tests/test_governance.py:367`, `backend/tests/test_governance.py:414`, `backend/tests/test_operations.py:125` | Step-up required before member changes/merge/restore (`403` before, success after) | sufficient | No direct negative test for expired step-up window timing edge | Add time-shift test for >10-minute expiry then mutation denied |
| Route authorization (RBAC) | `backend/tests/test_governance.py:59`, `backend/tests/test_operations.py:574`, `backend/tests/test_operations.py:605` | Planner denied admin routes; auditor read-only on ops | sufficient | None major | Add matrix test asserting all mutating ops endpoints reject AUDITOR |
| Object-level authorization (project membership + assignment) | `backend/tests/test_planner.py:185`, `backend/tests/test_resource_center.py:157`, `backend/tests/test_message_center.py:239` | Unscoped/readonly planner blocked (`403/404`) | sufficient | None major | Add direct negative tests for cross-project asset download IDs |
| Tenant isolation (cross-org) | `backend/tests/test_governance.py:76`, `backend/tests/test_planner.py:250`, `backend/tests/test_operations.py:621` | Cross-org actions return `404/422`, backup restore scope mismatch rejected | sufficient | None major | Add additional cross-org lineage/audit query filter assertions |
| Planner calculations + warnings | `backend/tests/test_planner.py:85` | Asserts distance/time positive, overlap and 12h warnings | sufficient | No extreme coordinate/pathological data case | Add edge tests for identical coordinates and large route chains |
| CSV/XLSX import/export receipts | `backend/tests/test_planner.py:277`, `backend/tests/test_planner.py:315`, `backend/tests/test_planner.py:360` | Mixed valid/invalid rows and receipt counts/hints | sufficient | No malformed XLSX structure fuzzing | Add invalid workbook structure cases |
| Sync package integrity/conflict/token auth | `backend/tests/test_planner.py:457`, `backend/tests/test_planner.py:518`, `backend/tests/test_planner.py:567` | Integrity flag, checksum mismatch, conflict outcome, bearer token flow | sufficient | No replay/idempotency stress case | Add repeated import race/idempotency assertions |
| Resource upload controls (MIME/signature/size) + cleanup | `backend/tests/test_resource_center.py:128`, `backend/tests/test_resource_center.py:142`, `backend/tests/test_resource_center.py:191` | Mismatch rejected, oversize rejected, cleanup deletes only eligible assets | basically covered | Missing coverage for assets becoming unreferenced via retention/cascade FK nulling | Add integration test: archive/delete itinerary (or retention prune), assert orphaned asset receives cleanup eligibility and is deleted after grace window |
| Message center variable rendering + caps + offline connectors | `backend/tests/test_message_center.py:81` | Hourly/daily caps, preview rendering, offline connector failed status | sufficient | No timezone-boundary day rollover test | Add UTC day-boundary cap reset tests |
| Audit/lineage immutability and retention lifecycle | `backend/tests/test_operations.py:468`, `backend/tests/test_operations.py:278` | Immutable update/delete fail; stale audit/lineage pruned at 365d | sufficient | No DB-engine parity test beyond current cases | Add explicit Postgres integration immutability verification in CI env |
| Frontend/backend operations retention contract parity | `frontend/tests/e2e/admin-governance.spec.ts:49` | E2E covers retention save/backup/restore flow | insufficient | No assertion for audit/lineage retention/deletion fields in UI/API types | Add unit/e2e assertions for these fields in operations UI |

### 8.3 Security Coverage Audit
- **Authentication:** basically covered (`backend/tests/test_auth.py:1`, `backend/tests/test_auth.py:55`), but cookie hardening config gap is not tested.
- **Route authorization:** sufficiently covered (`backend/tests/test_governance.py:59`, `backend/tests/test_operations.py:605`).
- **Object-level authorization:** sufficiently covered (`backend/tests/test_planner.py:185`, `backend/tests/test_resource_center.py:157`).
- **Tenant/data isolation:** sufficiently covered (`backend/tests/test_planner.py:250`, `backend/tests/test_operations.py:621`).
- **Admin/internal protection:** basically covered (`backend/tests/test_operations.py:574`, `backend/tests/test_operations.py:605`).
- **Residual severe-defect escape risk:** Security-hardening misconfigurations at deployment/config level (for example cookie security flags) can still pass current tests.

### 8.4 Final Coverage Judgment
- **Partial Pass**
- Major functional/security paths are broadly covered, but uncovered config-hardening assertions (notably session-cookie `Secure` expectations) mean tests could still pass while a material security defect remains.

## 9. Final Notes
- This report is strictly static and evidence-based; no runtime success is claimed.
- Most Prompt requirements are implemented with substantial test evidence.
- Acceptance is currently blocked by the high-severity cookie-security runtime configuration issue.

