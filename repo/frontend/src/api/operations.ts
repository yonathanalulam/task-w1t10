import { apiGet, apiPatch, apiPost } from "./client";

export type RetentionPolicy = {
  id: string;
  org_id: string;
  itinerary_retention_days: number;
  updated_by_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type RetentionRun = {
  id: string;
  org_id: string;
  initiated_by_user_id: string | null;
  status: string;
  deleted_itinerary_count: number;
  summary: string | null;
  started_at: string;
  completed_at: string | null;
};

export type BackupRun = {
  id: string;
  org_id: string;
  initiated_by_user_id: string | null;
  trigger_kind: string;
  status: string;
  backup_file_name: string | null;
  backup_file_path: string | null;
  encrypted_size_bytes: number | null;
  rotated_file_count: number;
  summary: string | null;
  started_at: string;
  completed_at: string | null;
};

export type RestoreRun = {
  id: string;
  org_id: string;
  initiated_by_user_id: string | null;
  status: string;
  backup_file_name: string;
  restored_table_count: number;
  summary: string | null;
  started_at: string;
  completed_at: string | null;
};

export type AuditEvent = {
  id: string;
  org_id: string;
  project_id: string | null;
  actor_user_id: string | null;
  action_type: string;
  resource_type: string;
  resource_id: string | null;
  request_method: string;
  request_path: string;
  status_code: number;
  detail_summary: string | null;
  metadata_json: Record<string, unknown> | null;
  occurred_at: string;
};

export type LineageEvent = {
  id: string;
  org_id: string;
  project_id: string | null;
  dataset_id: string | null;
  itinerary_id: string | null;
  created_by_user_id: string | null;
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
};

export const operationsApi = {
  getRetentionPolicy: () => apiGet<RetentionPolicy>("/api/ops/retention-policy"),
  updateRetentionPolicy: (itineraryRetentionDays: number) =>
    apiPatch<RetentionPolicy>("/api/ops/retention-policy", { itinerary_retention_days: itineraryRetentionDays }),
  runRetentionNow: () => apiPost<RetentionRun>("/api/ops/retention/run", {}),
  listRetentionRuns: (limit = 20) => apiGet<RetentionRun[]>(`/api/ops/retention/runs?limit=${encodeURIComponent(String(limit))}`),

  runBackupNow: () => apiPost<BackupRun>("/api/ops/backups/run", {}),
  listBackupRuns: (limit = 20) => apiGet<BackupRun[]>(`/api/ops/backups/runs?limit=${encodeURIComponent(String(limit))}`),

  runRestore: (backupFileName: string) => apiPost<RestoreRun>("/api/ops/restore", { backup_file_name: backupFileName }),
  listRestoreRuns: (limit = 20) => apiGet<RestoreRun[]>(`/api/ops/restore/runs?limit=${encodeURIComponent(String(limit))}`),

  listAuditEvents: (limit = 100) => apiGet<AuditEvent[]>(`/api/ops/audit/events?limit=${encodeURIComponent(String(limit))}`),
  listLineageEvents: (limit = 100) =>
    apiGet<LineageEvent[]>(`/api/ops/lineage/events?limit=${encodeURIComponent(String(limit))}`)
};
