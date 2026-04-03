# TrailForge design plan

## Product scope

TrailForge is an offline-first itinerary management system for travel operations teams. It runs on a local network over HTTPS and provides governed itinerary planning, resource/file handling, import/export plus offline sync, notification drafting, RBAC, auditability, lineage, retention, and backup/restore operations.

## Locked planning decisions

- Frontend: Vue 3 + Vite + TypeScript + Vue Router + Pinia.
- Backend: FastAPI + SQLAlchemy + Alembic + Pydantic.
- Runtime: `docker compose up --build`.
- Full test command: `./run_tests.sh`.
- Excel scope for v1: `.xlsx` plus CSV; no legacy `.xls`.
- Multi-org model: single TrailForge instance, strict org isolation, each user belongs to exactly one org in v1.
- Secure collaboration in v1: shared org workspace, project membership, itinerary assignment, governed edits, autosave/version history, audit/history, in-app messaging timeline. No comments/mentions/live co-editing in v1.
- Planner speed hierarchy: org defaults -> itinerary override -> day override.
- Sync conflict policy: fast-forward only; conflicting imports never silently overwrite and instead enter conflict receipt/manual resolution flow.
- Backup key handling: encrypted backups use a local key file stored outside the repo with OS-level protections.
- File signature validation depth: extension + detected MIME + basic signature/magic-byte validation, with quarantine support and future scanning hooks.

## Core domain interpretation

- **Dataset**: governed attraction catalog container with data-quality, duplicate-detection, and merge controls.
- **Project**: collaboration workspace grouping itineraries, members, linked datasets, assets, and related timeline activity.
- **Itinerary**: project-bound travel plan with days, stops, autosave/version history, warnings, and exports.

## System architecture

### Frontend modules

- `workspace-shell`: authentication bootstrap, org/project context, role-aware navigation.
- `admin-governance`: org settings, roles/permissions, dataset/project management, retention, backups.
- `dataset-center`: dataset CRUD, attraction CRUD, duplicate review, merge flow.
- `project-center`: project CRUD, membership, planner assignment.
- `planner`: itinerary/day/stop editing, drag-and-drop reorder, autosave state, warning surfaces, version history.
- `imports-exports`: CSV/XLSX import/export, sync-package import/export, receipts, conflict views.
- `resource-center`: uploads, previews/cards, validation outcomes, quarantine state, linked assets.
- `message-center`: templates, variable preview, send flow, timeline, cap feedback.

### Backend modules

- `auth`: login/logout/session bootstrap, step-up auth, token lifecycle.
- `rbac`: org and project-scoped authorization enforcement.
- `organizations`: org metadata and settings.
- `projects`: project CRUD, membership, assignment rules, dataset linking.
- `datasets`: dataset CRUD and ownership.
- `catalog`: attractions, dedupe keys, merge workflow, validation.
- `planner`: itinerary CRUD, stop reorder, autosave/versioning, travel and schedule warnings, speed resolution.
- `imports_exports`: CSV/XLSX parsers, exporters, row receipts.
- `sync`: package creation/import, checksums, conflict detection and queueing.
- `assets`: file validation, storage abstraction, metadata persistence, quarantine, cleanup eligibility.
- `messaging`: templates, render preview, in-app delivery attempts, capping, channel stubs.
- `audit_lineage`: immutable audit events, lineage records, redaction rules.
- `ops`: retention jobs, backup rotation, restore runs, cleanup jobs.

## Cross-cutting contracts

### Authentication and sensitive actions

- Browser usage uses secure session cookies.
- Device sync/internal integrations use revocable API tokens with 30-day default expiry.
- Sensitive actions such as permission changes, bulk merges, restore operations, and bulk conflict resolution require password re-entry within the last 10 minutes.

### Security

- Local-network HTTPS is required and documented via a locally generated certificate workflow.
- Passwords are stored with Argon2id hashing.
- Stored credential/token material is protected at rest, including encrypted bearer-token material.
- Sensitive log fields are masked.
- Audit logs are immutable and retained for 1 year.

### Governance and data integrity

- Validation runs on direct writes and batch imports.
- Attraction duration must remain within 5-720 minutes.
- Duplicate detection uses normalized `name + city + state` deterministic keys.
- Merge operations preserve audit/history and lineage.
- Itinerary retention defaults to 3 years and is configurable.

### Planner behavior

- Travel distance is computed from locally stored coordinates.
- Travel time uses configured urban/highway speeds.
- Warnings appear for overlapping schedule items at >=15 minutes and for days exceeding 12 hours of activities.
- Reordering is immediate in the UI and backed by autosave/versioning.

### File handling

- Max file size: 20 MB.
- Allowlist: PDF, DOCX, XLSX, CSV, JPG, PNG.
- Reject extension vs detected MIME mismatches.
- Apply basic signature validation.
- Persist checksums and quarantine state.
- Remove unreferenced assets after 30 days.

### Sync and imports

- CSV/XLSX import always produces accepted/rejected row outcomes plus correction hints.
- Offline sync packages are versioned archives containing manifest metadata, data payloads, checksums, and referenced assets.
- Sync import conflicts are surfaced for manual resolution; no silent overwrite.

### Messaging

- In-app messages are the required delivery surface.
- Template variables render previews and sent content.
- Frequency capping limits are 3 messages per user per day and 1 per hour per template category.
- SMS/email/push remain interface stubs only in v1.

### Offline operations

- Nightly encrypted backups write to a designated local folder with 14-day rotation.
- Restore is a real operator flow and must be documented and verified.
- No committed `.env` files are allowed.

## Planned delivery slices

1. Foundation + tenancy + auth/RBAC.
2. Dataset/project governance surfaces.
3. Catalog dedupe/merge.
4. Planner core.
5. Import/export receipts.
6. Offline sync package and conflict handling.
7. Resource center.
8. Message center.
9. Ops hardening: retention, backups, restore verification.
