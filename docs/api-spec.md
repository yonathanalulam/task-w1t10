# TrailForge API specification

## Base behavior

- Backend base path: `/api`
- Browser auth uses secure session cookies plus CSRF double-submit protection on mutating requests.
- Device/integration sync supports bearer API tokens.
- RBAC roles delivered: `ORG_ADMIN`, `PLANNER`, `AUDITOR`.
- Sensitive governance and restore actions require recent step-up authentication.

## Health

- `GET /health/live`
- `GET /health/ready`

## Authentication

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/step-up`
- `POST /auth/tokens`
- `GET /auth/tokens`
- `DELETE /auth/tokens/{token_id}`

## Governance

- `GET /admin/users`
- `GET /datasets`
- `POST /datasets`
- `PATCH /datasets/{dataset_id}`
- `GET /datasets/{dataset_id}/attractions`
- `POST /datasets/{dataset_id}/attractions`
- `PATCH /datasets/{dataset_id}/attractions/{attraction_id}`
- `GET /datasets/{dataset_id}/attractions/duplicates`
- `POST /datasets/{dataset_id}/attractions/merge`
- `GET /projects`
- `POST /projects`
- `PATCH /projects/{project_id}`
- `GET /projects/{project_id}/members`
- `POST /projects/{project_id}/members`
- `PATCH /projects/{project_id}/members/{member_id}`
- `DELETE /projects/{project_id}/members/{member_id}`
- `POST /projects/{project_id}/datasets/{dataset_id}`
- `DELETE /projects/{project_id}/datasets/{dataset_id}`

## Planner

- `GET /planner/projects`
- `GET /planner/users`
- `GET /projects/{project_id}/catalog/attractions`
- `GET /projects/{project_id}/itineraries`
- `POST /projects/{project_id}/itineraries`
- `GET /projects/{project_id}/itineraries/{itinerary_id}`
- `PATCH /projects/{project_id}/itineraries/{itinerary_id}`
- `DELETE /projects/{project_id}/itineraries/{itinerary_id}`
- `POST /projects/{project_id}/itineraries/{itinerary_id}/days`
- `PATCH /projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}`
- `DELETE /projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}`
- `POST /projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops`
- `PATCH /projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}`
- `DELETE /projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}`
- `POST /projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/reorder`
- `GET /projects/{project_id}/itineraries/{itinerary_id}/versions`

## Imports, exports, sync

- `GET /projects/{project_id}/itineraries/{itinerary_id}/export?format=csv|xlsx`
- `POST /projects/{project_id}/itineraries/{itinerary_id}/import`
- `GET /projects/{project_id}/sync-package/export`
- `POST /projects/{project_id}/sync-package/import`

## Resource center

- `GET /projects/{project_id}/resources/attractions/{attraction_id}/assets`
- `POST /projects/{project_id}/resources/attractions/{attraction_id}/assets`
- `GET /projects/{project_id}/resources/itineraries/{itinerary_id}/assets`
- `POST /projects/{project_id}/resources/itineraries/{itinerary_id}/assets`
- `GET /projects/{project_id}/resources/assets/{asset_id}/download`
- `DELETE /projects/{project_id}/resources/assets/{asset_id}`

## Message center

- `GET /projects/{project_id}/message-center/templates`
- `POST /projects/{project_id}/message-center/templates`
- `PATCH /projects/{project_id}/message-center/templates/{template_id}`
- `POST /projects/{project_id}/message-center/preview`
- `POST /projects/{project_id}/message-center/send`
- `GET /projects/{project_id}/message-center/timeline`

## Operations and audit

- `GET /ops/retention-policy`
- `PATCH /ops/retention-policy`
- `POST /ops/retention/run`
- `GET /ops/retention/runs`
- `POST /ops/backups/run`
- `GET /ops/backups/runs`
- `POST /ops/restore`
- `GET /ops/restore/runs`
- `GET /ops/audit/events`
- `GET /ops/lineage/events`

## Scope notes

- Planner, resources, messaging, and sync are project-scoped.
- Audit/history read surfaces are available to org admins and auditors; mutation surfaces remain org-admin-only.
- Backup and restore are organization-scoped in the delivered implementation and reject cross-org restore attempts.
