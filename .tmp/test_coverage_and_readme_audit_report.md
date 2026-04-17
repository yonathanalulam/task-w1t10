# Test Coverage Audit

## Project Type Detection
- Declared at top of README: `fullstack` (evidence: `README.md:3`).

## Backend Endpoint Inventory
Resolved prefixes:
- Global API prefix: `/api` (evidence: `backend/app/api/routes/__init__.py:12`).
- Operations sub-prefix: `/ops` (evidence: `backend/app/api/routes/operations.py:30`).
- Root endpoint outside `/api`: `/` (evidence: `backend/app/main.py:35`).

Total unique endpoints detected: **71**

1. `GET /`
2. `GET /api/health/live`
3. `GET /api/health/ready`
4. `POST /api/auth/login`
5. `POST /api/auth/logout`
6. `GET /api/auth/me`
7. `POST /api/auth/step-up`
8. `POST /api/auth/tokens`
9. `GET /api/auth/tokens`
10. `DELETE /api/auth/tokens/{token_id}`
11. `GET /api/admin/users`
12. `GET /api/datasets`
13. `POST /api/datasets`
14. `PATCH /api/datasets/{dataset_id}`
15. `GET /api/datasets/{dataset_id}/attractions`
16. `POST /api/datasets/{dataset_id}/attractions`
17. `GET /api/datasets/{dataset_id}/attractions/duplicates`
18. `POST /api/datasets/{dataset_id}/attractions/merge`
19. `PATCH /api/datasets/{dataset_id}/attractions/{attraction_id}`
20. `GET /api/projects`
21. `POST /api/projects`
22. `PATCH /api/projects/{project_id}`
23. `GET /api/projects/{project_id}/members`
24. `POST /api/projects/{project_id}/members`
25. `PATCH /api/projects/{project_id}/members/{member_id}`
26. `DELETE /api/projects/{project_id}/members/{member_id}`
27. `GET /api/projects/{project_id}/datasets`
28. `POST /api/projects/{project_id}/datasets/{dataset_id}`
29. `DELETE /api/projects/{project_id}/datasets/{dataset_id}`
30. `GET /api/planner/projects`
31. `GET /api/planner/users`
32. `GET /api/projects/{project_id}/catalog/attractions`
33. `GET /api/projects/{project_id}/itineraries`
34. `POST /api/projects/{project_id}/itineraries`
35. `GET /api/projects/{project_id}/itineraries/{itinerary_id}`
36. `PATCH /api/projects/{project_id}/itineraries/{itinerary_id}`
37. `DELETE /api/projects/{project_id}/itineraries/{itinerary_id}`
38. `POST /api/projects/{project_id}/itineraries/{itinerary_id}/days`
39. `PATCH /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}`
40. `DELETE /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}`
41. `POST /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops`
42. `PATCH /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}`
43. `DELETE /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}`
44. `POST /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/reorder`
45. `GET /api/projects/{project_id}/itineraries/{itinerary_id}/export`
46. `POST /api/projects/{project_id}/itineraries/{itinerary_id}/import`
47. `GET /api/projects/{project_id}/sync-package/export`
48. `POST /api/projects/{project_id}/sync-package/import`
49. `GET /api/projects/{project_id}/itineraries/{itinerary_id}/versions`
50. `GET /api/projects/{project_id}/resources/attractions/{attraction_id}/assets`
51. `POST /api/projects/{project_id}/resources/attractions/{attraction_id}/assets`
52. `GET /api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets`
53. `POST /api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets`
54. `GET /api/projects/{project_id}/resources/assets/{asset_id}/download`
55. `DELETE /api/projects/{project_id}/resources/assets/{asset_id}`
56. `GET /api/projects/{project_id}/message-center/templates`
57. `POST /api/projects/{project_id}/message-center/templates`
58. `PATCH /api/projects/{project_id}/message-center/templates/{template_id}`
59. `POST /api/projects/{project_id}/message-center/preview`
60. `POST /api/projects/{project_id}/message-center/send`
61. `GET /api/projects/{project_id}/message-center/timeline`
62. `GET /api/ops/retention-policy`
63. `PATCH /api/ops/retention-policy`
64. `POST /api/ops/retention/run`
65. `GET /api/ops/retention/runs`
66. `POST /api/ops/backups/run`
67. `GET /api/ops/backups/runs`
68. `POST /api/ops/restore`
69. `GET /api/ops/restore/runs`
70. `GET /api/ops/audit/events`
71. `GET /api/ops/lineage/events`

## API Test Mapping Table

| Endpoint | Covered | Test type | Test files | Evidence |
|---|---|---|---|---|
| GET / | yes | true no-mock HTTP | `test_health.py` | `backend/tests/test_health.py:test_root_returns_minimal_service_status` |
| GET /api/health/live | yes | true no-mock HTTP | `test_health.py` | `backend/tests/test_health.py:test_liveness` |
| GET /api/health/ready | yes | true no-mock HTTP | `test_health.py` | `backend/tests/test_health.py:test_readiness` |
| POST /api/auth/login | yes | true no-mock HTTP | `test_auth.py`, others | `backend/tests/test_auth.py:test_login_and_me` |
| POST /api/auth/logout | yes | true no-mock HTTP | `test_governance.py`, `test_operations.py`, `test_planner.py` | `backend/tests/test_governance.py:test_org_isolation_blocks_cross_org_access` |
| GET /api/auth/me | yes | true no-mock HTTP | `test_auth.py`, `test_api_auth_negative.py` | `backend/tests/test_auth.py:test_login_and_me` |
| POST /api/auth/step-up | yes | true no-mock HTTP | multiple | `backend/tests/test_auth.py:test_step_up_marks_session` |
| POST /api/auth/tokens | yes | true no-mock HTTP | `test_auth.py`, `test_planner.py` | `backend/tests/test_auth.py:test_api_token_lifecycle` |
| GET /api/auth/tokens | yes | true no-mock HTTP | `test_auth.py`, `test_planner.py` | `backend/tests/test_auth.py:test_api_token_lifecycle` |
| DELETE /api/auth/tokens/{token_id} | yes | true no-mock HTTP | `test_auth.py` | `backend/tests/test_auth.py:test_api_token_lifecycle` |
| GET /api/admin/users | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| GET /api/datasets | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_planner_cannot_access_admin_governance_routes` |
| POST /api/datasets | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_org_admin_can_manage_datasets_projects_and_links` |
| PATCH /api/datasets/{dataset_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_org_isolation_blocks_cross_org_access` |
| GET /api/datasets/{dataset_id}/attractions | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_org_admin_can_manage_attractions_duplicates_and_merge` |
| POST /api/datasets/{dataset_id}/attractions | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_org_admin_can_manage_attractions_duplicates_and_merge` |
| GET /api/datasets/{dataset_id}/attractions/duplicates | yes | true no-mock HTTP | `test_governance.py` | `backend/tests/test_governance.py:test_org_admin_can_manage_attractions_duplicates_and_merge` |
| POST /api/datasets/{dataset_id}/attractions/merge | yes | true no-mock HTTP | `test_governance.py`, `test_operations.py` | `backend/tests/test_governance.py:test_org_admin_can_manage_attractions_duplicates_and_merge` |
| PATCH /api/datasets/{dataset_id}/attractions/{attraction_id} | yes | true no-mock HTTP | `test_governance.py`, `test_operations.py` | `backend/tests/test_governance.py:test_attraction_org_isolation_blocks_cross_org_access` |
| GET /api/projects | yes | true no-mock HTTP | multiple | `backend/tests/test_operations.py:test_ops_retention_backup_restore_and_audit` |
| POST /api/projects | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_org_admin_can_manage_datasets_projects_and_links` |
| PATCH /api/projects/{project_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| GET /api/projects/{project_id}/members | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| POST /api/projects/{project_id}/members | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_project_membership_management` |
| PATCH /api/projects/{project_id}/members/{member_id} | yes | true no-mock HTTP | `test_governance.py` | `backend/tests/test_governance.py:test_project_membership_management` |
| DELETE /api/projects/{project_id}/members/{member_id} | yes | true no-mock HTTP | `test_governance.py` | `backend/tests/test_governance.py:test_project_membership_management` |
| GET /api/projects/{project_id}/datasets | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_org_admin_can_manage_datasets_projects_and_links` |
| POST /api/projects/{project_id}/datasets/{dataset_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_governance.py:test_org_admin_can_manage_datasets_projects_and_links` |
| DELETE /api/projects/{project_id}/datasets/{dataset_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| GET /api/planner/projects | yes | true no-mock HTTP | `test_planner.py` | `backend/tests/test_planner.py:test_planner_project_scoping_and_assignment_guards` |
| GET /api/planner/users | yes | true no-mock HTTP | `test_api_surface_smoke.py` | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| GET /api/projects/{project_id}/catalog/attractions | yes | true no-mock HTTP | `test_api_surface_smoke.py` | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| GET /api/projects/{project_id}/itineraries | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| POST /api/projects/{project_id}/itineraries | yes | true no-mock HTTP | multiple | `backend/tests/test_planner.py:test_planner_core_workflow_with_versions_and_warnings` |
| GET /api/projects/{project_id}/itineraries/{itinerary_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| PATCH /api/projects/{project_id}/itineraries/{itinerary_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| DELETE /api/projects/{project_id}/itineraries/{itinerary_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| POST /api/projects/{project_id}/itineraries/{itinerary_id}/days | yes | true no-mock HTTP | multiple | `backend/tests/test_planner.py:test_planner_core_workflow_with_versions_and_warnings` |
| PATCH /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| DELETE /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| POST /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops | yes | true no-mock HTTP | multiple | `backend/tests/test_planner.py:test_planner_core_workflow_with_versions_and_warnings` |
| PATCH /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_planner.py:test_planner_core_workflow_with_versions_and_warnings` |
| DELETE /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id} | yes | true no-mock HTTP | multiple | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| POST /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/reorder | yes | true no-mock HTTP | `test_planner.py` | `backend/tests/test_planner.py:test_planner_core_workflow_with_versions_and_warnings` |
| GET /api/projects/{project_id}/itineraries/{itinerary_id}/export | yes | true no-mock HTTP | `test_planner.py` | `backend/tests/test_planner.py:test_planner_export_csv_and_xlsx` |
| POST /api/projects/{project_id}/itineraries/{itinerary_id}/import | yes | true no-mock HTTP (+ mocked variants exist) | `test_planner.py`, `test_operations.py` | no-mock: `backend/tests/test_planner.py:test_planner_import_csv_receipt_with_mixed_valid_invalid_rows`; mocked: `backend/tests/test_planner.py:test_planner_import_accepts_file_just_under_20_mb_limit` |
| GET /api/projects/{project_id}/sync-package/export | yes | true no-mock HTTP | `test_planner.py`, `test_operations.py` | `backend/tests/test_planner.py:test_sync_package_export_import_and_conflict_policy` |
| POST /api/projects/{project_id}/sync-package/import | yes | true no-mock HTTP (+ mocked variants exist) | `test_planner.py` | no-mock: `backend/tests/test_planner.py:test_sync_package_export_import_and_conflict_policy`; mocked: `backend/tests/test_planner.py:test_sync_package_import_accepts_file_just_under_20_mb_limit` |
| GET /api/projects/{project_id}/itineraries/{itinerary_id}/versions | yes | true no-mock HTTP | `test_planner.py` | `backend/tests/test_planner.py:test_planner_core_workflow_with_versions_and_warnings` |
| GET /api/projects/{project_id}/resources/attractions/{attraction_id}/assets | yes | true no-mock HTTP | `test_resource_center.py` | `backend/tests/test_resource_center.py:test_resource_center_upload_list_download_and_unreference` |
| POST /api/projects/{project_id}/resources/attractions/{attraction_id}/assets | yes | true no-mock HTTP | `test_resource_center.py` | `backend/tests/test_resource_center.py:test_resource_center_upload_list_download_and_unreference` |
| GET /api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets | yes | true no-mock HTTP | `test_resource_center.py` | `backend/tests/test_resource_center.py:test_resource_center_upload_list_download_and_unreference` |
| POST /api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets | yes | true no-mock HTTP | `test_resource_center.py` | `backend/tests/test_resource_center.py:test_resource_center_upload_list_download_and_unreference` |
| GET /api/projects/{project_id}/resources/assets/{asset_id}/download | yes | true no-mock HTTP | `test_resource_center.py` | `backend/tests/test_resource_center.py:test_resource_center_upload_list_download_and_unreference` |
| DELETE /api/projects/{project_id}/resources/assets/{asset_id} | yes | true no-mock HTTP | `test_resource_center.py` | `backend/tests/test_resource_center.py:test_resource_center_upload_list_download_and_unreference` |
| GET /api/projects/{project_id}/message-center/templates | yes | true no-mock HTTP | `test_message_center.py` | `backend/tests/test_message_center.py:test_message_center_read_only_project_member_can_view_but_not_mutate` |
| POST /api/projects/{project_id}/message-center/templates | yes | true no-mock HTTP | `test_message_center.py` | `backend/tests/test_message_center.py:test_message_center_template_preview_send_timeline_and_caps` |
| PATCH /api/projects/{project_id}/message-center/templates/{template_id} | yes | true no-mock HTTP | `test_message_center.py` | `backend/tests/test_message_center.py:test_message_center_template_preview_send_timeline_and_caps` |
| POST /api/projects/{project_id}/message-center/preview | yes | true no-mock HTTP | `test_message_center.py` | `backend/tests/test_message_center.py:test_message_center_template_preview_send_timeline_and_caps` |
| POST /api/projects/{project_id}/message-center/send | yes | true no-mock HTTP | `test_message_center.py` | `backend/tests/test_message_center.py:test_message_center_template_preview_send_timeline_and_caps` |
| GET /api/projects/{project_id}/message-center/timeline | yes | true no-mock HTTP | `test_message_center.py` | `backend/tests/test_message_center.py:test_message_center_template_preview_send_timeline_and_caps` |
| GET /api/ops/retention-policy | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_ops_retention_backup_restore_and_audit` |
| PATCH /api/ops/retention-policy | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_ops_retention_backup_restore_and_audit` |
| POST /api/ops/retention/run | yes | true no-mock HTTP | `test_api_surface_smoke.py` | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| GET /api/ops/retention/runs | yes | true no-mock HTTP | `test_api_surface_smoke.py` | `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` |
| POST /api/ops/backups/run | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_ops_retention_backup_restore_and_audit` |
| GET /api/ops/backups/runs | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_auditor_can_read_ops_history_but_cannot_mutate` |
| POST /api/ops/restore | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_ops_retention_backup_restore_and_audit` |
| GET /api/ops/restore/runs | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_ops_restore_failure_records_for_wrong_key_and_corrupt_payload` |
| GET /api/ops/audit/events | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_ops_retention_backup_restore_and_audit` |
| GET /api/ops/lineage/events | yes | true no-mock HTTP | `test_operations.py` | `backend/tests/test_operations.py:test_ops_lineage_visibility_and_immutable_tables` |

## API Test Classification

### 1) True No-Mock HTTP
- Real HTTP layer via `TestClient(app)` fixture (evidence: `backend/tests/conftest.py:167-169`).
- Real route stack exercised with DB-backed dependencies and no global route/service mocks in most endpoint tests.

### 2) HTTP with Mocking
- Planner import path monkeypatching in HTTP tests:
  - `backend/tests/test_planner.py:test_planner_import_rejects_oversized_upload` (`backend/tests/test_planner.py:631`)
  - `backend/tests/test_planner.py:test_sync_package_import_rejects_oversized_upload` (`backend/tests/test_planner.py:646`)
  - `backend/tests/test_planner.py:test_planner_import_accepts_file_just_under_20_mb_limit` (`backend/tests/test_planner.py:691`)
  - `backend/tests/test_planner.py:test_sync_package_import_accepts_file_just_under_20_mb_limit` (`backend/tests/test_planner.py:732`)

### 3) Non-HTTP (unit/integration without HTTP)
- Direct service/module tests in:
  - `backend/tests/test_bootstrap.py`
  - `backend/tests/test_logging.py`
  - service-level sections of `backend/tests/test_operations.py`
  - lock/serialization section in `backend/tests/test_message_center.py:test_message_send_serializes_frequency_check_with_org_lock`
  - cleanup-cycle sections in `backend/tests/test_resource_center.py`

## Mock Detection Rules Audit
- No evidence of `jest.mock`, `vi.mock`, or `sinon.stub` in backend tests.
- Mock-like behavior exists via `pytest` monkeypatch:
  - planner route helper/service monkeypatches (`backend/tests/test_planner.py:631`, `backend/tests/test_planner.py:646`, `backend/tests/test_planner.py:691`, `backend/tests/test_planner.py:732`)
  - DB execute monkeypatch in service-level tests (`backend/tests/test_operations.py:516`, `backend/tests/test_message_center.py:325`)

## Coverage Summary
- Total endpoints: **71**
- Endpoints with HTTP tests: **71**
- Endpoints with true no-mock HTTP tests: **71**
- HTTP coverage: **100.0%**
- True API coverage: **100.0%**

Computation basis:
- `70/70` `/api` endpoint evidence rows (evidence: `backend/tests/route_test_matrix.md:78`)
- plus root endpoint `/` tested in `backend/tests/test_health.py:test_root_returns_minimal_service_status`.

## Unit Test Analysis

### Backend Unit Tests
Test files:
- `backend/tests/test_bootstrap.py`
- `backend/tests/test_logging.py`
- mixed unit/service sections in `backend/tests/test_operations.py`, `backend/tests/test_message_center.py`, `backend/tests/test_resource_center.py`

Modules covered:
- controllers/routes: full endpoint HTTP coverage across route modules
- services: bootstrap/auth/audit/operations/message_center/resource_center/planner flows
- repositories/data: ORM models and queries via real session fixtures
- auth/guards/middleware: CSRF/session/step-up/role gating via auth/governance/planner/ops tests

Important backend modules not directly unit-focused:
- `backend/app/api/deps.py` (covered indirectly through endpoint behavior)
- `backend/app/core/database.py` (indirect)
- `backend/app/core/security.py` (mostly indirect)

### Frontend Unit Tests (STRICT REQUIREMENT)
Detected frontend unit test files:
- `frontend/tests/unit/router-access.spec.ts`
- `frontend/tests/unit/auth-store.spec.ts`
- `frontend/tests/unit/api-client.spec.ts`
- `frontend/tests/unit/planner-utils.spec.ts`
- `frontend/tests/unit/message-center-utils.spec.ts`
- `frontend/tests/unit/attractions-validation.spec.ts`
- `frontend/tests/unit/login-view.spec.ts`
- `frontend/tests/unit/workspace-shell.spec.ts`
- `frontend/tests/unit/workspace-overview-view.spec.ts`

Framework/tools detected:
- Vitest + jsdom (evidence: `frontend/vitest.config.ts:7-10`)
- Vue Test Utils component rendering (evidence: `frontend/tests/unit/login-view.spec.ts:2`, `frontend/tests/unit/workspace-shell.spec.ts:2`, `frontend/tests/unit/workspace-overview-view.spec.ts:2`)

Frontend components/modules covered:
- components/views: `LoginView.vue`, `WorkspaceShell.vue`, `WorkspaceOverviewView.vue`
- state/routing/utils/api helpers: `stores/auth.ts`, `router/access.ts`, `api/client.ts`, `utils/planner.ts`, `utils/message-center.ts`, `utils/attractions.ts`

Important frontend components/modules not tested:
- `frontend/src/views/WorkspacePlannerView.vue`
- `frontend/src/views/WorkspaceMessageCenterView.vue`
- `frontend/src/views/WorkspaceOperationsView.vue`
- `frontend/src/views/WorkspaceDatasetsView.vue`
- `frontend/src/views/WorkspaceProjectsView.vue`
- `frontend/src/router/index.ts`

**Mandatory Verdict: Frontend unit tests: PRESENT**

### Cross-Layer Observation
- Backend and frontend both have direct unit-level evidence and E2E assets.
- Backend remains deeper in API breadth; frontend improved materially with real component render tests.

## API Observability Check
- Improved from previous state:
  - `backend/tests/test_api_surface_smoke.py:test_additional_route_surface_smoke` now asserts payload fields and list semantics, not only status codes.
  - `backend/tests/test_api_auth_negative.py` now asserts JSON error shape/content and cookie behavior on auth failures.
- Remaining weak spots: some tests still status-first in broader suites, but overall observability is **strong**.

## Test Quality & Sufficiency
- Success paths: strong and broad.
- Failure/edge/validation/authz: strong (401/403/404/409/413/422, token/csrf/session/step-up, org isolation, archive limits, checksum/compression checks).
- Integration boundaries: strong backend integration + Playwright E2E presence.
- Over-mocking: constrained to specific planner upload boundary cases; compensating no-mock endpoint tests exist.

## Tests Check
- `run_tests.sh` is Docker-based and containerized end-to-end (evidence: `run_tests.sh:5-21`).

## End-to-End Expectations
- Fullstack FE↔BE test assets present (`frontend/tests/e2e/*.spec.ts` and `frontend/playwright.config.ts`).
- Static audit only: execution not performed.

## Test Coverage Score (0-100)
**93/100**

## Score Rationale
- + Complete endpoint coverage with true no-mock HTTP evidence.
- + Strong auth/permission/edge-case assertions.
- + Frontend unit tests now include actual Vue component rendering behavior.
- - Some HTTP tests still use monkeypatch in selected paths.
- - Several frontend feature views remain untested at component level.

## Key Gaps
1. Planner import/sync upload tests still include monkeypatched route internals (`backend/tests/test_planner.py:691`, `backend/tests/test_planner.py:732`).
2. Critical frontend feature views (`WorkspacePlannerView`, `WorkspaceMessageCenterView`, `WorkspaceOperationsView`) still lack component-level unit coverage.

## Confidence & Assumptions
- Confidence: **high** (static endpoint list + direct test file evidence).
- Assumptions:
  - `backend/tests/route_test_matrix.md` is current.
  - No hidden dynamic route registration outside inspected route modules.

---

# README Audit

## README Location
- Present at required path: `README.md`.

## Hard Gate Failures
- **None identified** under current strict gate set.

## High Priority Issues
- None.

## Medium Priority Issues
- None.

## Low Priority Issues
- Optional reviewer walkthrough capture uses `npm run capture:important-flows` (`README.md:311-313`). This is not a hard-gate failure and not a runtime-install instruction.

## Engineering Quality
- Tech stack clarity: strong.
- Architecture and feature surface clarity: strong.
- Testing and verification instructions: now explicit and mostly compliant.
- Security/roles/workflows: clearly documented, including role credentials.

## Hard Gate Compliance Check
- Project type declaration at top: pass (`README.md:3`).
- Backend/fullstack startup includes literal `docker-compose up`: pass (`README.md:157`).
- Access method (URL+port): pass (`README.md:38`, `README.md:119-131`).
- Verification method present (API curl + web flow): pass (`README.md:186-229`).
- Environment rules (no runtime install steps like pip/npm install): pass (no such install commands present).
- Demo credentials for auth roles: pass (`README.md:235-239`), with implementation evidence in bootstrap service (`backend/app/services/bootstrap.py:42-46`, `backend/app/services/bootstrap.py:151-183`) and compose default (`docker-compose.yml:54`).

## README Verdict
**PASS**

Reason:
- Hard gates pass and readiness verification text now matches implementation (`README.md:203`, `backend/app/api/routes/health.py:18`).
