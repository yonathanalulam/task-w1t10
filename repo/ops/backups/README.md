# Backup and Restore Operations

TrailForge now includes encrypted backup and restore foundations with operator visibility in **Workspace → Operations**.

Backup/restore scope is organization-bound: each backup payload is tagged to one org and restore rejects scope-mismatched org attempts.

## Security/key model

- Backups are encrypted using a Fernet key from `TF_BACKUP_ENCRYPTION_KEY_PATH`.
- In Docker Compose local runtime, that key is generated into the runtime-secrets volume at:
  - `/run/secrets/backup_encryption_key`
- The key file is not committed to this repository and must be owner-only permissioned (for example `0600`).
- Treat this key as highly sensitive: without it, backups cannot be decrypted/restored.

## Backup storage and rotation

- Backup folder: `TF_BACKUP_ROOT` (default `/var/lib/trailforge/backups`)
- File format: encrypted `*.tfbak`
- Rotation: files older than `TF_BACKUP_ROTATION_DAYS` (default **14**) are removed when a backup run executes.

## Nightly backup support

Nightly encrypted backups are executed automatically by the Docker Compose `ops-daemon` service.

One-shot helper inside backend container (manual trigger):

```bash
docker compose exec backend python scripts/nightly_backup.py
```

The helper is optional and useful for manual/operator-triggered cycles.

## Operations daemon cycle behavior

- `ops-daemon` runs a periodic cycle (default every 300 seconds).
- On cycles where current UTC hour equals `TF_NIGHTLY_BACKUP_HOUR_UTC` (default `2`), it runs nightly backup creation for organizations lacking a successful nightly backup for that UTC day.
- Every cycle also executes resource-center cleanup deletion for assets that are:
  - unreferenced (`attraction_id` and `itinerary_id` are both null), and
  - `cleanup_eligible_at <= now`.
- Cleanup deletes object bytes and removes the DB row only after re-checking those conditions at deletion time.

## Manual operator flow (UI)

1. Go to `https://localhost:5173/workspace/operations`
2. Use **Run backup now** in the Nightly encrypted backups section
3. Confirm the run appears in backup run history

## Restore flow (real path)

1. Go to `https://localhost:5173/workspace/operations`
2. Perform **step-up verification** with your current password
3. Select a backup file from recorded backup runs
4. Click **Run restore**

Restore is destructive to the current organization's mutable runtime state and replays that organization's encrypted snapshot.
Existing immutable `audit_events` and `lineage_events` are preserved and restore only appends missing historical rows from the backup.

## Failure visibility

- Backup, restore, and retention executions persist run records for both success and failure states.
- Restore failures such as wrong-key decrypt errors and corrupt payload errors are captured in restore run history and surfaced in the Operations UI.

## API surface (ORG_ADMIN)

All backup/restore endpoints are org-scoped; restore rejects backups whose embedded org scope does not match the caller org.

- `GET /api/ops/backups/runs`
- `POST /api/ops/backups/run`
- `GET /api/ops/restore/runs`
- `POST /api/ops/restore` (requires recent step-up)
- `GET /api/ops/retention-policy`
- `PATCH /api/ops/retention-policy` (requires recent step-up)
- `POST /api/ops/retention/run`
- `GET /api/ops/retention/runs`
- `GET /api/ops/audit/events`
- `GET /api/ops/lineage/events`
