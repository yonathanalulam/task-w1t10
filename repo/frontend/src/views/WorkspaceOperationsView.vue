<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiError } from "../api/client";
import {
  AuditEvent,
  BackupRun,
  LineageEvent,
  RestoreRun,
  RetentionPolicy,
  RetentionRun,
  operationsApi
} from "../api/operations";
import { useAuthStore } from "../stores/auth";

const props = withDefaults(
  defineProps<{
    readOnly?: boolean;
  }>(),
  {
    readOnly: false
  }
);

const authStore = useAuthStore();

const loading = ref(false);
const error = ref<string | null>(null);
const success = ref<string | null>(null);

const retentionPolicy = ref<RetentionPolicy | null>(null);
const retentionDaysInput = ref("1095");
const retentionRuns = ref<RetentionRun[]>([]);
const backupRuns = ref<BackupRun[]>([]);
const restoreRuns = ref<RestoreRun[]>([]);
const auditEvents = ref<AuditEvent[]>([]);
const lineageEvents = ref<LineageEvent[]>([]);

const stepUpPassword = ref("");
const selectedRestoreFileName = ref("");

const savingPolicy = ref(false);
const runningRetention = ref(false);
const runningBackup = ref(false);
const runningRestore = ref(false);
const steppingUp = ref(false);
const canMutate = computed(() => authStore.isOrgAdmin && !props.readOnly);

const restorableBackupRuns = computed(() =>
  backupRuns.value.filter((row) => row.status === "succeeded" && Boolean(row.backup_file_name))
);

function setActionError(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    error.value = err.message;
    return;
  }
  error.value = err instanceof Error ? err.message : fallback;
}

async function loadOperations() {
  loading.value = true;
  error.value = null;
  try {
    const [policy, retentionRows, backupRows, restoreRows, auditRows, lineageRows] = await Promise.all([
      operationsApi.getRetentionPolicy(),
      operationsApi.listRetentionRuns(20),
      operationsApi.listBackupRuns(30),
      operationsApi.listRestoreRuns(20),
      operationsApi.listAuditEvents(100),
      operationsApi.listLineageEvents(100)
    ]);

    retentionPolicy.value = policy;
    retentionDaysInput.value = String(policy.itinerary_retention_days);
    retentionRuns.value = retentionRows;
    backupRuns.value = backupRows;
    restoreRuns.value = restoreRows;
    auditEvents.value = auditRows;
    lineageEvents.value = lineageRows;

    const selectedStillExists = restorableBackupRuns.value.some((row) => row.backup_file_name === selectedRestoreFileName.value);
    if (!selectedStillExists) {
      selectedRestoreFileName.value = restorableBackupRuns.value[0]?.backup_file_name ?? "";
    }
  } catch (err) {
    setActionError(err, "Failed to load operations center");
  } finally {
    loading.value = false;
  }
}

async function stepUpNow() {
  if (!stepUpPassword.value.trim()) {
    error.value = "Provide your password to complete step-up.";
    return;
  }

  steppingUp.value = true;
  error.value = null;
  success.value = null;
  try {
    await authStore.stepUp(stepUpPassword.value);
    success.value = "Step-up verified for sensitive operations.";
    stepUpPassword.value = "";
  } catch (err) {
    setActionError(err, "Step-up failed");
  } finally {
    steppingUp.value = false;
  }
}

async function saveRetentionPolicy() {
  const parsed = Number(retentionDaysInput.value);
  if (!Number.isInteger(parsed) || parsed < 30) {
    error.value = "Retention policy must be at least 30 days.";
    return;
  }

  savingPolicy.value = true;
  error.value = null;
  success.value = null;
  try {
    retentionPolicy.value = await operationsApi.updateRetentionPolicy(parsed);
    success.value = "Retention policy updated.";
    await loadOperations();
  } catch (err) {
    setActionError(err, "Failed to update retention policy");
  } finally {
    savingPolicy.value = false;
  }
}

async function runRetentionNow() {
  runningRetention.value = true;
  error.value = null;
  success.value = null;
  try {
    await operationsApi.runRetentionNow();
    success.value = "Retention run completed.";
    await loadOperations();
  } catch (err) {
    setActionError(err, "Retention run failed");
  } finally {
    runningRetention.value = false;
  }
}

async function runBackupNow() {
  runningBackup.value = true;
  error.value = null;
  success.value = null;
  try {
    const run = await operationsApi.runBackupNow();
    success.value = run.status === "succeeded" ? `Backup created: ${run.backup_file_name}` : `Backup ${run.status}.`;
    await loadOperations();
  } catch (err) {
    setActionError(err, "Backup run failed");
  } finally {
    runningBackup.value = false;
  }
}

async function runRestore() {
  if (!selectedRestoreFileName.value) {
    error.value = "Select a backup file to restore.";
    return;
  }

  runningRestore.value = true;
  error.value = null;
  success.value = null;
  try {
    const run = await operationsApi.runRestore(selectedRestoreFileName.value);
    success.value = `Restore completed from ${run.backup_file_name}.`;
    await loadOperations();
  } catch (err) {
    setActionError(err, "Restore failed");
  } finally {
    runningRestore.value = false;
  }
}

onMounted(loadOperations);
</script>

<template>
  <div>
    <h2>{{ canMutate ? "Organization Operations Center" : "Audit & Lineage" }}</h2>
    <p class="muted-inline">
      Audit trail, lineage visibility, retention execution history, encrypted backup history, and restore run history.
    </p>
    <p v-if="!canMutate" class="muted-inline">Read-only auditor mode. Mutating operations are restricted to org admins.</p>

    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="success" class="planner-import-receipt">{{ success }}</p>
    <p v-if="loading">Loading operations data...</p>

    <div class="admin-grid section-gap" v-if="!loading">
      <section class="panel stack" v-if="canMutate">
        <h3>Step-up for sensitive operations</h3>
        <label>
          Password
          <input v-model="stepUpPassword" type="password" data-testid="ops-step-up-password-input" />
        </label>
        <button class="btn" data-testid="ops-step-up-btn" :disabled="steppingUp" @click="stepUpNow">
          {{ steppingUp ? "Verifying..." : "Verify step-up" }}
        </button>
      </section>

      <section class="panel stack">
        <h3>Itinerary retention policy</h3>
        <p class="muted-inline">Default is 3 years (1095 days).</p>
        <label v-if="canMutate">
          Retention days
          <input v-model="retentionDaysInput" data-testid="ops-retention-days-input" type="number" min="30" />
        </label>
        <p v-else class="muted-inline">Configured retention days: {{ retentionPolicy?.itinerary_retention_days ?? "n/a" }}</p>
        <div class="actions-row" v-if="canMutate">
          <button class="btn" data-testid="ops-retention-save-btn" :disabled="savingPolicy" @click="saveRetentionPolicy">
            {{ savingPolicy ? "Saving..." : "Save policy" }}
          </button>
          <button
            class="btn btn-secondary"
            data-testid="ops-retention-run-btn"
            :disabled="runningRetention"
            @click="runRetentionNow"
          >
            {{ runningRetention ? "Running..." : "Run retention now" }}
          </button>
        </div>
        <ul class="list-items" v-if="retentionRuns.length">
          <li v-for="run in retentionRuns" :key="run.id" class="list-item" data-testid="ops-retention-run-item">
            <div>
              <strong>{{ run.status }}</strong>
              <p class="muted-inline">{{ run.started_at }} • deleted={{ run.deleted_itinerary_count }}</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="panel stack">
        <h3>Nightly encrypted backups</h3>
        <p class="muted-inline">
          Backups are organization-scoped, encrypted with a local key file, and rotated after 14 days.
        </p>
        <button v-if="canMutate" class="btn" data-testid="ops-backup-run-btn" :disabled="runningBackup" @click="runBackupNow">
          {{ runningBackup ? "Running backup..." : "Run backup now" }}
        </button>

        <ul class="list-items" v-if="backupRuns.length">
          <li v-for="run in backupRuns" :key="run.id" class="list-item" data-testid="ops-backup-run-item">
            <div>
              <strong>{{ run.status }} • {{ run.backup_file_name }}</strong>
              <p class="muted-inline">
                {{ run.started_at }} • trigger={{ run.trigger_kind }} • size={{ run.encrypted_size_bytes ?? 0 }} bytes •
                rotated={{ run.rotated_file_count }}
              </p>
              <p v-if="run.summary" class="muted-inline">{{ run.summary }}</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="panel stack" v-if="canMutate">
        <h3>Restore from backup</h3>
        <p class="warning-text">Restore requires recent step-up and overwrites this organization's data state.</p>
        <label>
          Backup file
          <select v-model="selectedRestoreFileName" data-testid="ops-restore-file-select">
            <option value="" disabled>Select backup file</option>
            <option v-for="run in restorableBackupRuns" :key="run.id" :value="run.backup_file_name || ''">
              {{ run.backup_file_name }}
            </option>
          </select>
        </label>
        <button class="btn" data-testid="ops-restore-run-btn" :disabled="runningRestore" @click="runRestore">
          {{ runningRestore ? "Restoring..." : "Run restore" }}
        </button>
      </section>

      <section class="panel stack">
        <h3>Restore run history</h3>
        <ul class="list-items" v-if="restoreRuns.length">
          <li v-for="run in restoreRuns" :key="run.id" class="list-item" data-testid="ops-restore-run-item">
            <div>
              <strong>{{ run.status }} • {{ run.backup_file_name }}</strong>
              <p class="muted-inline">{{ run.started_at }} • tables={{ run.restored_table_count }}</p>
              <p v-if="run.summary" class="muted-inline">{{ run.summary }}</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="panel panel-span stack">
        <h3>Audit trail (immutable)</h3>
        <ul class="list-items" v-if="auditEvents.length">
          <li v-for="event in auditEvents" :key="event.id" class="list-item" data-testid="ops-audit-event-item">
            <div>
              <strong>{{ event.action_type }}</strong>
              <p class="muted-inline">{{ event.occurred_at }} • {{ event.request_method }} {{ event.request_path }}</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="panel panel-span stack">
        <h3>Lineage events</h3>
        <ul class="list-items" v-if="lineageEvents.length">
          <li v-for="event in lineageEvents" :key="event.id" class="list-item" data-testid="ops-lineage-event-item">
            <div>
              <strong>{{ event.event_type }}</strong>
              <p class="muted-inline">
                {{ event.occurred_at }} • entity={{ event.entity_type }} {{ event.entity_id || "n/a" }} •
                project={{ event.project_id || "n/a" }}
              </p>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
