# TrailForge test coverage summary

## Primary verification commands

- Runtime: `docker compose up --build`
- Broad full suite: `./run_tests.sh`
- Local backend pytest: `cd backend && python3 -m pytest -q`
- Frontend unit/build: `cd frontend && npm run test:unit -- --run && npm run build`

## Current verified evidence

- Owner broad gate passed on the delivered stack:
  - backend container suite: 36 passed
  - frontend unit suite: 19 passed
  - Playwright suite: 9 passed
- Local backend pytest path was remediated to be self-contained and then passed from a clean local repo context:
  - `42 passed`
- Focused remediation verification also covered:
  - sensitive-action step-up enforcement
  - auditor read-only access paths
  - org-scoped backup/restore isolation
  - frontend session-freshness revalidation

## Backend coverage areas

- auth login/logout/session bootstrap
- API token creation, revocation, expiry handling
- role and org isolation enforcement
- datasets/projects governance CRUD
- membership permission mutations with step-up enforcement
- duplicate detection and merge with step-up enforcement
- planner itinerary/day/stop CRUD, reorder, warnings, versions, deletes
- CSV/XLSX import/export receipts
- sync-package export/import and conflict handling
- resource-center validation, uploads, downloads, cleanup behavior
- message-center template CRUD, preview, send, caps, timeline
- operations retention, backups, restore, audit, lineage

## Route evidence

- Owner-readable route matrix artifact: `repo/backend/tests/route_test_matrix.md`
- Current evidence maps `70/70` declared API routes to test references.
- This matrix is evidence support for route coverage review; it is not runtime tracing instrumentation.

## Frontend coverage areas

- route access and role-aware navigation
- auth store and API client behavior
- planner utility logic
- message placeholder rendering utilities
- browser flows for governance, planner, imports/exports, sync, resource center, message center, operations, and session freshness

## Coverage boundaries

- Backend API tests are real in-process HTTP-style tests through FastAPI `TestClient`, not separate-process HTTPS runtime tests.
- Full HTTPS/browser/runtime proof is covered by the owner-run Docker gate and Playwright suite rather than local pytest alone.
- Playwright auth-required specs now resolve credentials from supported sources, but still depend on a valid runtime/bootstrap source being available.
