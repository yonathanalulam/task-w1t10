# TrailForge (Slices 1-9 Foundation)

**Project type: fullstack**

TrailForge is an offline-first itinerary management platform for travel operations teams.

This repository currently provides a production-oriented foundation through **Slice 1 + Slice 2 + Slice 3 + Slice 4 + Slice 5 + Slice 6 + Slice 7 + Slice 8 + Slice 9**:

- local-network HTTPS runtime with Docker Compose
- PostgreSQL-backed FastAPI app with Alembic migrations baseline
- real auth/session plumbing with step-up session model groundwork
- CSRF enforcement for cookie-authenticated mutation endpoints
- RBAC role/permission scaffolding and bootstrap org/admin provisioning
- Vue 3 + TypeScript + Vite frontend with router, Pinia auth store, login flow, and authenticated workspace shell
- backend, frontend, and Playwright test stack scaffolding
- organization-admin datasets management
- organization-admin projects management
- project membership management (`role_in_project` + `can_edit` foundations)
- dataset-to-project linking/unlinking
- org-isolated governance APIs and admin workspace UI
- governed attraction CRUD under datasets
- deterministic duplicate detection using normalized `name + city + state`
- duplicate review and merge workflow with merge-event history snapshots
- planner-core itinerary workflow with day/stop planning, drag-reorder, warnings, and version history
- planner itinerary import/export with CSV/XLSX support, row-level import receipts, 20 MB upload ceilings, and XLSX archive entry/uncompressed-size hardening
- offline sync package export/import with manifest+checksum integrity checks, conflict-aware apply results, 20 MB upload ceilings, and ZIP entry/uncompressed-size hardening
- project-scoped resource center for attraction/itinerary assets with controlled media validation, upload progress, previews, checksums, cleanup-eligibility marking, and automatic grace-period cleanup execution
- project-scoped message center with reusable templates, variable render preview, in-app drafting/send flow, delivery-attempt timeline, offline connector abstraction points, and enforced frequency caps
- immutable audit-trail events for sensitive domain/operator actions with query surface
- lineage-event foundations for merge/import/sync visibility
- configurable itinerary retention policy (default 3 years) plus strict 1-year audit/lineage retention with operator run visibility
- encrypted backup/restore foundations with organization-scoped UI/API behavior, automatic nightly run support, 14-day backup rotation, and persisted success/failure run history

## What exists now

### Backend

- FastAPI app over HTTPS (`https://localhost:8443`)
- health endpoints:
  - `GET /api/health/live`
  - `GET /api/health/ready`
- auth endpoints:
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
  - `POST /api/auth/step-up`
  - `POST /api/auth/tokens`
  - `GET /api/auth/tokens`
  - `DELETE /api/auth/tokens/{token_id}`
- governance endpoints (ORG_ADMIN):
  - `GET /api/admin/users`
  - `GET/POST /api/datasets`
  - `PATCH /api/datasets/{dataset_id}`
  - `GET/POST /api/datasets/{dataset_id}/attractions`
  - `PATCH /api/datasets/{dataset_id}/attractions/{attraction_id}`
  - `GET /api/datasets/{dataset_id}/attractions/duplicates`
  - `POST /api/datasets/{dataset_id}/attractions/merge` (requires recent step-up)
  - `GET/POST /api/projects`
  - `PATCH /api/projects/{project_id}`
  - `GET /api/projects/{project_id}/members`
  - `POST /api/projects/{project_id}/members` (requires recent step-up)
  - `PATCH/DELETE /api/projects/{project_id}/members/{member_id}` (requires recent step-up)
  - `GET /api/projects/{project_id}/datasets`
  - `POST /api/projects/{project_id}/datasets/{dataset_id}`
  - `DELETE /api/projects/{project_id}/datasets/{dataset_id}`
- planner endpoints (ORG_ADMIN + PLANNER with project scoping):
  - `GET /api/planner/projects`
  - `GET /api/planner/users`
  - `GET /api/projects/{project_id}/catalog/attractions`
  - `GET/POST /api/projects/{project_id}/itineraries`
  - `GET/PATCH/DELETE /api/projects/{project_id}/itineraries/{itinerary_id}`
  - `POST /api/projects/{project_id}/itineraries/{itinerary_id}/days`
  - `PATCH/DELETE /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}`
  - `POST /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops`
  - `PATCH/DELETE /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}`
  - `POST /api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/reorder`
  - `GET /api/projects/{project_id}/itineraries/{itinerary_id}/export?format=csv|xlsx`
  - `POST /api/projects/{project_id}/itineraries/{itinerary_id}/import` (multipart CSV/XLSX)
  - `GET /api/projects/{project_id}/sync-package/export` (ZIP sync package)
  - `POST /api/projects/{project_id}/sync-package/import` (multipart ZIP sync package)
  - `GET /api/projects/{project_id}/itineraries/{itinerary_id}/versions`
  - `GET /api/projects/{project_id}/resources/attractions/{attraction_id}/assets`
  - `POST /api/projects/{project_id}/resources/attractions/{attraction_id}/assets`
  - `GET /api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets`
  - `POST /api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets`
  - `GET /api/projects/{project_id}/resources/assets/{asset_id}/download`
  - `DELETE /api/projects/{project_id}/resources/assets/{asset_id}` (marks cleanup eligibility; `ops-daemon` deletes after 30-day grace period)
  - `GET /api/projects/{project_id}/message-center/templates`
  - `POST /api/projects/{project_id}/message-center/templates`
  - `PATCH /api/projects/{project_id}/message-center/templates/{template_id}`
  - `POST /api/projects/{project_id}/message-center/preview`
  - `POST /api/projects/{project_id}/message-center/send`
  - `GET /api/projects/{project_id}/message-center/timeline`
  - `GET /api/ops/retention-policy` (ORG_ADMIN + AUDITOR)
  - `PATCH /api/ops/retention-policy` (requires recent step-up)
  - `POST /api/ops/retention/run`
  - `GET /api/ops/retention/runs` (ORG_ADMIN + AUDITOR)
  - `POST /api/ops/backups/run`
  - `GET /api/ops/backups/runs` (ORG_ADMIN + AUDITOR)
  - `POST /api/ops/restore` (requires recent step-up)
  - `GET /api/ops/restore/runs` (ORG_ADMIN + AUDITOR)
  - `GET /api/ops/audit/events` (ORG_ADMIN + AUDITOR)
  - `GET /api/ops/lineage/events` (ORG_ADMIN + AUDITOR)
- sync-package endpoints support either:
  - browser session + CSRF header (`X-CSRF-Token`), or
  - `Authorization: Bearer <api_token>` for device/integration transfer paths
- cookie-session mutation endpoints enforce CSRF via double-submit token:
  - CSRF cookie: `trailforge_csrf`
  - required header on mutating requests: `X-CSRF-Token`
- PostgreSQL schema baseline via Alembic
- bootstrap logic that creates:
  - default org (`default-org`)
  - roles: `ORG_ADMIN`, `PLANNER`, `AUDITOR`
  - permissions mapped to those roles
  - one bootstrap `admin` user with one-time generated password

### Frontend

- Vue login screen at `https://localhost:5173/login`
- authenticated workspace shell at `https://localhost:5173/workspace`
- workspace governance surfaces:
  - `https://localhost:5173/workspace/datasets`
  - `https://localhost:5173/workspace/projects`
- planner workspace surface:
  - `https://localhost:5173/workspace/planner`
- message center workspace surface:
  - `https://localhost:5173/workspace/messages`
- operations workspace surface (ORG_ADMIN):
  - `https://localhost:5173/workspace/operations`
- auditor workspace surface (read-only history/log view):
  - `https://localhost:5173/workspace/audit`
- dataset surface includes attraction catalog CRUD plus duplicate review/merge workflow
- planner surface includes itinerary/day/stop CRUD, project-linked attraction catalog adds, drag-and-drop stop ordering, overlap/activity warnings, save-state/version feedback, CSV/XLSX import/export with row-level receipts, offline sync package export/import with conflict outcome visibility, and resource-center attraction/itinerary asset workflows with upload progress + server validation feedback + image/document previews
- message center surface includes reusable template management, real placeholder rendering preview (`traveler_name`, `departure_time`, etc.), in-app send workflow, and persisted message + delivery-attempt timeline with enforced caps (max 3/day/user, max 1/hour/category/user)
- operations surface includes immutable audit timeline, lineage event visibility for merge/import/sync, retention policy + run history, encrypted backup runs, and restore flow with step-up enforcement
- org-scoped backup/restore applies only to the caller's organization data, rejects cross-org restore attempts, and preserves existing immutable audit/lineage history with append-only restore semantics
- non-admin/non-auditor users are intentionally gated from admin and audit routes and redirected to an in-app restricted surface
- Pinia auth bootstrap/login/logout/step-up store
- route guards tied to server-validated session state (auth state is refreshed on navigation)

### Testing scaffold

- backend tests: pytest
- frontend tests: Vitest + jsdom
- E2E tests: Playwright (Chromium)
- backend route-to-test evidence matrix:
  - `cd backend && python scripts/route_test_matrix.py`
  - output: `backend/tests/route_test_matrix.md`

## Primary commands

### Launch

Canonical Docker startup (required form):

```bash
docker-compose up
```

The modern Docker CLI also accepts the space form and, for a full rebuild:

```bash
docker compose up --build
```

For temporary local HTTP testing without changing `docker-compose.yml`, start Compose from a shell that overrides the secure-cookie setting:

```bash
TF_SESSION_COOKIE_SECURE=false docker-compose up
```

Leave the variable unset for the default secure HTTPS runtime.

### Full test suite

The full test suite is Docker-only and runs inside the `backend-tests`, `frontend-tests`, and `e2e-tests` Compose services:

```bash
./run_tests.sh
```

`run_tests.sh` orchestrates `docker compose` profiles; no local language toolchain is required. Runtime dependencies (Python, Node, Postgres, Playwright) are provided entirely by Docker images.

## Verification

### API verification (curl)

All backend endpoints are served over HTTPS at `https://localhost:8443` with a self-signed cert (use `-k` for local trust). A green stack answers all three of these:

1. Liveness probe:

    ```bash
    curl -k -i https://localhost:8443/api/health/live
    # Expected: HTTP/1.1 200 OK
    # Expected body: {"status":"ok"}
    ```

2. Readiness probe (executes a trivial DB query before responding):

    ```bash
    curl -k -i https://localhost:8443/api/health/ready
    # Expected: HTTP/1.1 200 OK
    # Expected body: {"status":"ready"}
    ```

3. Demo login (ORG_ADMIN) — see **Demo credentials** below:

    ```bash
    curl -k -i -c cookies.txt \
      -H "Content-Type: application/json" \
      -d '{"org_slug":"default-org","username":"demo-admin","password":"TrailForgeDemo!123"}' \
      https://localhost:8443/api/auth/login
    # Expected: HTTP/1.1 200 OK
    # Expected body: {"user":{"username":"demo-admin","roles":["ORG_ADMIN"], ...}}

    curl -k -b cookies.txt https://localhost:8443/api/auth/me
    # Expected: HTTP/1.1 200 OK with the same user payload
    ```

### Web UI verification checklist

Open `https://localhost:5173` in a browser (accept the self-signed cert) and walk through:

- [ ] `/login` renders the TrailForge sign-in card with Organization, Username, and Password fields.
- [ ] Sign in with `default-org` / `demo-admin` / `TrailForgeDemo!123` → redirected to `/workspace`.
- [ ] Workspace sidebar shows **Overview**, **Planner**, **Message Center**, **Datasets**, **Projects**, **Operations** for ORG_ADMIN.
- [ ] Sign out, sign back in as `demo-planner` / `TrailForgeDemo!123` → sidebar shows Planner + Message Center only (no Datasets/Projects/Operations).
- [ ] Sign out, sign back in as `demo-auditor` / `TrailForgeDemo!123` → sidebar shows Audit & Lineage; mutation buttons on visible surfaces are absent.
- [ ] Visiting `/workspace/operations` as the auditor redirects to the restricted surface (no 500 page).

## Demo credentials

The backend provisions deterministic, non-production demo seed users during bootstrap for local Docker/dev so reviewers can sign in without running the encrypted bootstrap helper. **These users are intended only for local development and must not be used in production.**

| Role | Organization | Username | Password |
|---|---|---|---|
| ORG_ADMIN | `default-org` | `demo-admin` | `TrailForgeDemo!123` |
| PLANNER | `default-org` | `demo-planner` | `TrailForgeDemo!123` |
| AUDITOR | `default-org` | `demo-auditor` | `TrailForgeDemo!123` |

Demo seeding is controlled by `TF_DEMO_SEED_USERS` (default `true` in `docker-compose.yml`). Set `TF_DEMO_SEED_USERS=false` to skip demo user provisioning.

### First-run bootstrap admin (optional, encrypted)

In addition to the demo users above, the backend also writes one-time encrypted bootstrap credentials for a long-lived `admin` user to:

```text
/bootstrap/admin_credentials.txt
```

Read and consume it once with:

```bash
docker compose exec backend python scripts/read_bootstrap_credentials.py
```

The helper decrypts the envelope and deletes it after a successful read.

Change credentials in later slices via admin flows (not implemented yet).

## Runtime secret bootstrap (no committed static secrets)

- Compose runs an `init-secrets` one-shot service that generates a random Postgres password into a Docker volume (`trailforge_runtime_secrets`) on first run.
- Postgres uses `POSTGRES_PASSWORD_FILE` from that volume.
- Backend composes its DB URL at runtime from the same password file.
- Backup encryption key is generated at runtime into the same secret volume (`/run/secrets/backup_encryption_key`) and used for encrypted backup files.
- Compose also runs an `ops-daemon` service that executes periodic operations cycles: nightly encrypted backups, retention cleanup (including strict 1-year audit/lineage enforcement), and cleanup deletion for unreferenced assets that have passed the 30-day grace window.
- No committed `.env` file or committed static DB password is used.

If you intentionally reset local runtime state, remove both DB and runtime secret volumes together:

```bash
docker compose down -v
```

## HTTPS notes

- TrailForge auto-generates a self-signed cert into Docker volume `trailforge_certs` if none exists.
- Browser trust setup/custom cert instructions are in `ops/certs/README.md`.

## Backup and restore operations notes

- Operator guide: `ops/backups/README.md`
- Backups are encrypted and written under `TF_BACKUP_ROOT` (default `/var/lib/trailforge/backups`) with 14-day rotation.
- Backup and restore scope is tenant-safe: each backup snapshot is bound to one organization and restore only applies to that same organization.
- Restore replays mutable org-scoped business data while preserving existing immutable audit and lineage history as append-only records.
- Automatic nightly backup execution is provided by the Compose `ops-daemon` runtime service.
- One-shot helper command (manual trigger) remains available:

```bash
docker compose exec backend python scripts/nightly_backup.py
```

## E2E bootstrap credential resolution

Playwright E2E specs resolve bootstrap credentials in this order:

1. `E2E_ORG_SLUG` + `E2E_USERNAME` + `E2E_PASSWORD` env vars
2. `E2E_BOOTSTRAP_CREDS_FILE` consumed through `frontend/scripts/read_bootstrap_credentials.mjs`
3. `/bootstrap/admin_credentials.txt` consumed through `frontend/scripts/read_bootstrap_credentials.mjs`
4. `/tmp/trailforge-e2e-runtime/bootstrap/admin_credentials.txt` consumed through `frontend/scripts/read_bootstrap_credentials.mjs`
5. running `docker compose exec -T backend python scripts/read_bootstrap_credentials.py`

The helper decrypts the bootstrap envelope and removes it after successful use, which keeps the password off disk in plaintext while preserving runtime bootstrap for CI and local review flows.

## Reviewer walkthrough video capture

To generate a slow-paced Playwright walkthrough video of important TrailForge flows (login, governance, planner, operations):

```bash
cd frontend
npm run capture:important-flows -- /home/yonim/trailForge/submission/trailforge-important-flows.webm
```

The capture script uses the same runtime credential resolution order as E2E specs and records against the live app at `https://localhost:5173`.

## No env files policy

- This repo does **not** use committed `.env` files.
- Runtime config is provided by Docker Compose environment variables and generated runtime artifacts in Docker volumes.

## What is intentionally upcoming

- deeper audit analytics/reporting and SIEM-forward integrations
- backup offsite replication and disaster-recovery orchestration
