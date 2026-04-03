# TrailForge clarification questions

Status: approved
Approved on: 2026-04-02

This file is the clarification question record for TrailForge. The full original prompt is preserved in `../metadata.json`. The developer-facing implementation brief lives in `../.ai/clarification-prompt.md`.

## Questions asked to the user

### 1) Can the drafted clarification defaults be used for planning?

- **Why this was asked:** the prompt was large enough that planning needed explicit confirmation that the clarification package was acceptable.
- **Answer:** yes — proceed with the drafted defaults.
- **Effect on execution:** planning could start from the approved clarification brief instead of carrying uncertainty forward.

### 2) What offline deployment style should the initial build assume?

- **Why this was asked:** the prompt required a fully offline system but did not force a specific local deployment mechanism.
- **Answer:** use Docker Compose as the default offline deployment path.
- **Effect on execution:** the project runtime contract uses `docker compose up --build` as the primary launch command.

### 3) How should Excel support be handled in the first implementation pass?

- **Why this was asked:** the prompt required CSV/Excel support but did not specify whether legacy `.xls` was required.
- **Answer:** support `.xlsx` plus CSV; do not include legacy `.xls` in the first pass.
- **Effect on execution:** import/export planning and validation target `.xlsx` rather than the older Excel format.

## Safe defaults locked during clarification

These were treated as safe defaults because they sharpen execution without narrowing the approved product intent.

### Frontend implementation default

- **Decision:** Vue 3 + Vite + TypeScript + Vue Router + Pinia.
- **Rationale:** the prompt already required a Vue workspace and a modern frontend framework. This default keeps the implementation conventional and strong without changing product scope.

### Backend implementation default

- **Decision:** FastAPI + SQLAlchemy + Alembic + Pydantic.
- **Rationale:** the prompt already required FastAPI and PostgreSQL. These choices provide the expected persistence, schema, and migration foundations.

### Offline sync package shape

- **Decision:** use a versioned portable archive containing manifest metadata, serialized payloads, checksums, and referenced assets.
- **Rationale:** the prompt required an offline sync package for cross-device transfer but did not define the file structure.

### HTTPS setup approach

- **Decision:** use a locally generated certificate workflow and document trust/setup steps.
- **Rationale:** the prompt required local-network HTTPS, so clarification locked a practical offline-safe way to satisfy it.

### Resource preview behavior for non-image files

- **Decision:** use document preview/file cards for non-image assets, with stronger thumbnail behavior where applicable.
- **Rationale:** the prompt required thumbnail previews and controlled media handling, but non-image assets need a different presentation than images.

### Reserved outbound connector approach

- **Decision:** keep SMS/email/push as provider abstraction points and disabled placeholders in v1.
- **Rationale:** the prompt explicitly said those connectors should be reserved but not required for offline operation.

### Scheduled operations approach

- **Decision:** backups, retention cleanup, and orphan-file cleanup will run as app-managed scheduled jobs suitable for a single-node offline deployment.
- **Rationale:** the prompt required these recurring operations but did not prescribe the scheduling mechanism.

## Non-assumptions intentionally preserved during clarification

These were kept open during clarification so the prompt would not be narrowed too early.

- **Secure collaboration:** clarification did not prematurely force either live collaboration or non-live collaboration.
- **Excel support before approval:** clarification did not assume `.xlsx`-only support until the user explicitly approved it.
- **File validation semantics:** clarification kept basic signature validation explicit alongside MIME and extension validation.

## Clarification risks carried into planning

- Offline HTTPS must remain usable in a real local-network setup.
- Drag-and-drop reorder plus autosave cannot be brittle or laggy.
- Import receipts must stay readable and actionable at row level.
- File validation must stay strict on extension, MIME, and signature checks.
- Backup and restore must be real operator flows, not placeholders.

## Clarification outcome

- The clarification package was validated for prompt faithfulness before approval.
- User approval was obtained for the planning baseline.
- Planning was allowed to proceed from the approved clarification brief.
