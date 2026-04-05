<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { ApiError } from "../api/client";
import { ResourceAsset, ResourceAssetUploadResult, resourceCenterApi } from "../api/resource-center";
import {
  Itinerary,
  ItineraryDay,
  ItineraryImportReceipt,
  ItineraryListItem,
  ItineraryVersion,
  PlannerCatalogAttraction,
  PlannerProject,
  PlannerUser,
  SyncPackageImportReceipt,
  plannerApi
} from "../api/planner";
import { useAuthStore } from "../stores/auth";
import { clockInputToMinutes, minutesToClockInput, reorderIds } from "../utils/planner";

type DaySaveState = "idle" | "saving" | "saved" | "error";

const authStore = useAuthStore();

const loadingProjects = ref(false);
const loadingWorkspace = ref(false);
const savingItinerary = ref(false);
const loadingItinerary = ref(false);
const error = ref<string | null>(null);
const importingItinerary = ref(false);
const exportingFormat = ref<"csv" | "xlsx" | null>(null);
const exportingSyncPackage = ref(false);
const importingSyncPackage = ref(false);
const loadingResourceAssets = ref(false);
const uploadingAttractionAsset = ref(false);
const uploadingItineraryAsset = ref(false);
const attractionUploadProgress = ref(0);
const itineraryUploadProgress = ref(0);

const projects = ref<PlannerProject[]>([]);
const plannerUsers = ref<PlannerUser[]>([]);
const catalogAttractions = ref<PlannerCatalogAttraction[]>([]);
const itineraries = ref<ItineraryListItem[]>([]);
const versions = ref<ItineraryVersion[]>([]);

const selectedProjectId = ref("");
const selectedItinerary = ref<Itinerary | null>(null);
const selectedImportFile = ref<File | null>(null);
const importReceipt = ref<ItineraryImportReceipt | null>(null);
const selectedSyncPackageFile = ref<File | null>(null);
const syncPackageReceipt = ref<SyncPackageImportReceipt | null>(null);
const selectedResourceAttractionId = ref("");
const selectedAttractionAssetFile = ref<File | null>(null);
const selectedItineraryAssetFile = ref<File | null>(null);
const attractionAssetInputRef = ref<HTMLInputElement | null>(null);
const itineraryAssetInputRef = ref<HTMLInputElement | null>(null);
const attractionAssetInputVersion = ref(0);
const itineraryAssetInputVersion = ref(0);
const attractionAssets = ref<ResourceAsset[]>([]);
const itineraryAssets = ref<ResourceAsset[]>([]);
const lastAttractionUploadValidation = ref<ResourceAssetUploadResult["validation"] | null>(null);
const lastItineraryUploadValidation = ref<ResourceAssetUploadResult["validation"] | null>(null);

const daySaveStates = ref<Record<string, DaySaveState>>({});
const draggingStopByDay = ref<Record<string, string | null>>({});

const itineraryForm = reactive({
  name: "",
  description: "",
  status: "draft",
  assignedPlannerUserId: "",
  urbanSpeedOverride: "",
  highwaySpeedOverride: ""
});

const dayForm = reactive({
  dayNumber: "1",
  title: ""
});

const stopForms = reactive<Record<string, { attractionId: string; startClock: string; duration: string; notes: string }>>({});

const canEditSelectedProject = computed(
  () => projects.value.find((project) => project.id === selectedProjectId.value)?.can_edit ?? false
);

const selectedProject = computed(() => projects.value.find((project) => project.id === selectedProjectId.value) ?? null);
const attractionUploadReady = computed(() => {
  attractionAssetInputVersion.value;
  const hasFile = !!selectedAttractionAssetFile.value || !!attractionAssetInputRef.value?.files?.[0];
  return !!selectedResourceAttractionId.value && hasFile;
});
const itineraryUploadReady = computed(() => {
  itineraryAssetInputVersion.value;
  const hasFile = !!selectedItineraryAssetFile.value || !!itineraryAssetInputRef.value?.files?.[0];
  return !!activeResourceItineraryId() && hasFile;
});
const plannerFormLocked = computed(() => loadingWorkspace.value || loadingItinerary.value);
const resourceCenterLocked = computed(() => loadingWorkspace.value || loadingItinerary.value || savingItinerary.value);

let workspaceLoadToken = 0;
let itineraryLoadToken = 0;

function activeResourceItineraryId(): string | null {
  return selectedItinerary.value?.id ?? itineraries.value[0]?.id ?? null;
}

function activeResourceItineraryName(): string {
  return selectedItinerary.value?.name ?? itineraries.value[0]?.name ?? "";
}

function setActionError(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    error.value = err.message;
    return;
  }
  error.value = err instanceof Error ? err.message : fallback;
}

function setDaySaveState(dayId: string, state: DaySaveState) {
  daySaveStates.value[dayId] = state;
  if (state === "saved") {
    window.setTimeout(() => {
      if (daySaveStates.value[dayId] === "saved") {
        daySaveStates.value[dayId] = "idle";
      }
    }, 1500);
  }
}

function daySaveStateLabel(dayId: string): string {
  const state = daySaveStates.value[dayId] ?? "idle";
  if (state === "saving") return "Saving...";
  if (state === "saved") return "Saved";
  if (state === "error") return "Save failed";
  return "";
}

function resetItineraryForm() {
  itineraryForm.name = "";
  itineraryForm.description = "";
  itineraryForm.status = "draft";
  itineraryForm.assignedPlannerUserId = "";
  itineraryForm.urbanSpeedOverride = "";
  itineraryForm.highwaySpeedOverride = "";
}

function hydrateItineraryForm(itinerary: Itinerary) {
  itineraryForm.name = itinerary.name;
  itineraryForm.description = itinerary.description ?? "";
  itineraryForm.status = itinerary.status;
  itineraryForm.assignedPlannerUserId = itinerary.assigned_planner_user_id ?? "";
  itineraryForm.urbanSpeedOverride = itinerary.urban_speed_mph_override == null ? "" : String(itinerary.urban_speed_mph_override);
  itineraryForm.highwaySpeedOverride =
    itinerary.highway_speed_mph_override == null ? "" : String(itinerary.highway_speed_mph_override);
}

function ensureStopForm(day: ItineraryDay) {
  if (stopForms[day.id]) return;
  const firstAttraction = catalogAttractions.value[0];
  stopForms[day.id] = {
    attractionId: firstAttraction?.id ?? "",
    startClock: "09:00",
    duration: firstAttraction ? String(firstAttraction.duration_minutes) : "60",
    notes: ""
  };
}

function getStopForm(day: ItineraryDay) {
  ensureStopForm(day);
  return stopForms[day.id];
}

async function loadProjects() {
  loadingProjects.value = true;
  error.value = null;
  try {
    projects.value = await plannerApi.listPlannerProjects();
    plannerUsers.value = await plannerApi.listAssignablePlanners();
    if (!selectedProjectId.value && projects.value.length > 0) {
      selectedProjectId.value = projects.value[0].id;
      await loadProjectWorkspace();
    }
  } catch (err) {
    setActionError(err, "Failed to load planner projects");
  } finally {
    loadingProjects.value = false;
  }
}

async function loadProjectWorkspace() {
  if (!selectedProjectId.value) return;
  const token = ++workspaceLoadToken;
  loadingWorkspace.value = true;
  error.value = null;
  try {
    const [catalogRes, itinerariesRes] = await Promise.all([
      plannerApi.listProjectCatalogAttractions(selectedProjectId.value),
      plannerApi.listItineraries(selectedProjectId.value)
    ]);

    if (token !== workspaceLoadToken) return;

    selectedItinerary.value = null;
    selectedImportFile.value = null;
    importReceipt.value = null;
    selectedSyncPackageFile.value = null;
    syncPackageReceipt.value = null;
    versions.value = [];
    attractionAssets.value = [];
    itineraryAssets.value = [];
    selectedResourceAttractionId.value = "";
    selectedAttractionAssetFile.value = null;
    selectedItineraryAssetFile.value = null;
    lastAttractionUploadValidation.value = null;
    lastItineraryUploadValidation.value = null;
    resetItineraryForm();

    catalogAttractions.value = catalogRes;
    itineraries.value = itinerariesRes;
    selectedResourceAttractionId.value = catalogRes[0]?.id ?? "";
    await loadResourceAssets();
  } catch (err) {
    if (token !== workspaceLoadToken) return;
    setActionError(err, "Failed to load planner workspace");
  } finally {
    if (token !== workspaceLoadToken) return;
    loadingWorkspace.value = false;
  }
}

function formatBytes(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  const kb = sizeBytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}

async function loadResourceAssets() {
  if (!selectedProjectId.value) return;
  loadingResourceAssets.value = true;
  try {
    attractionAssets.value = selectedResourceAttractionId.value
      ? await resourceCenterApi.listAttractionAssets(selectedProjectId.value, selectedResourceAttractionId.value)
      : [];

    const itineraryId = activeResourceItineraryId();
    itineraryAssets.value = itineraryId
      ? await resourceCenterApi.listItineraryAssets(selectedProjectId.value, itineraryId)
      : [];
  } catch (err) {
    setActionError(err, "Failed to load resource assets");
  } finally {
    loadingResourceAssets.value = false;
  }
}

function onAttractionAssetFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  attractionAssetInputVersion.value += 1;
  selectedAttractionAssetFile.value = target.files?.[0] ?? null;
}

function onItineraryAssetFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  itineraryAssetInputVersion.value += 1;
  selectedItineraryAssetFile.value = target.files?.[0] ?? null;
}

async function uploadAttractionAsset() {
  const file = selectedAttractionAssetFile.value ?? attractionAssetInputRef.value?.files?.[0] ?? null;
  if (!selectedProjectId.value || !selectedResourceAttractionId.value || !file) {
    error.value = "Select an attraction and a file before uploading.";
    return;
  }
  uploadingAttractionAsset.value = true;
  attractionUploadProgress.value = 0;
  error.value = null;
  try {
    const upload = await resourceCenterApi.uploadAttractionAsset(
      selectedProjectId.value,
      selectedResourceAttractionId.value,
      file,
      (percent) => {
        attractionUploadProgress.value = percent;
      }
    );
    selectedAttractionAssetFile.value = null;
    if (attractionAssetInputRef.value) {
      attractionAssetInputRef.value.value = "";
    }
    attractionAssetInputVersion.value += 1;
    lastAttractionUploadValidation.value = upload.validation;
    await loadResourceAssets();
  } catch (err) {
    setActionError(err, "Failed to upload attraction asset");
  } finally {
    uploadingAttractionAsset.value = false;
  }
}

async function uploadItineraryAsset() {
  const itineraryId = activeResourceItineraryId();
  const file = selectedItineraryAssetFile.value ?? itineraryAssetInputRef.value?.files?.[0] ?? null;
  if (!selectedProjectId.value || !itineraryId || !file) {
    error.value = "Select a file before uploading.";
    return;
  }
  uploadingItineraryAsset.value = true;
  itineraryUploadProgress.value = 0;
  error.value = null;
  try {
    const upload = await resourceCenterApi.uploadItineraryAsset(
      selectedProjectId.value,
      itineraryId,
      file,
      (percent) => {
        itineraryUploadProgress.value = percent;
      }
    );
    selectedItineraryAssetFile.value = null;
    if (itineraryAssetInputRef.value) {
      itineraryAssetInputRef.value.value = "";
    }
    itineraryAssetInputVersion.value += 1;
    lastItineraryUploadValidation.value = upload.validation;
    await loadResourceAssets();
  } catch (err) {
    setActionError(err, "Failed to upload itinerary asset");
  } finally {
    uploadingItineraryAsset.value = false;
  }
}

async function unreferenceAsset(asset: ResourceAsset) {
  if (!selectedProjectId.value || !canEditSelectedProject.value) return;
  try {
    await resourceCenterApi.unreferenceAsset(selectedProjectId.value, asset.id);
    await loadResourceAssets();
  } catch (err) {
    setActionError(err, "Failed to unreference asset");
  }
}

async function onResourceAttractionScopeChange() {
  await loadResourceAssets();
}

async function selectItinerary(itineraryId: string, options?: { resetImportReceipt?: boolean }) {
  if (!selectedProjectId.value) return;
  const token = ++itineraryLoadToken;
  loadingItinerary.value = true;
  error.value = null;
  try {
    const [itineraryRes, versionsRes] = await Promise.all([
      plannerApi.getItinerary(selectedProjectId.value, itineraryId),
      plannerApi.listVersions(selectedProjectId.value, itineraryId)
    ]);

    if (token !== itineraryLoadToken) return;

    selectedItinerary.value = itineraryRes;
    if (options?.resetImportReceipt ?? true) {
      importReceipt.value = null;
    }
    selectedImportFile.value = null;
    versions.value = versionsRes;
    hydrateItineraryForm(itineraryRes);
    for (const day of itineraryRes.days) {
      ensureStopForm(day);
      setDaySaveState(day.id, "idle");
    }
    await loadResourceAssets();
  } catch (err) {
    if (token !== itineraryLoadToken) return;
    setActionError(err, "Failed to load itinerary details");
  } finally {
    if (token !== itineraryLoadToken) return;
    loadingItinerary.value = false;
  }
}

async function refreshSelectedItinerary() {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  await selectItinerary(selectedItinerary.value.id, { resetImportReceipt: false });
  itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
  await loadResourceAssets();
}

function parseOptionalSpeed(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

async function createItineraryFromForm() {
  if (!selectedProjectId.value) return;
  savingItinerary.value = true;
  error.value = null;
  try {
    const itinerary = await plannerApi.createItinerary(selectedProjectId.value, {
      name: itineraryForm.name,
      description: itineraryForm.description,
      status: itineraryForm.status,
      assigned_planner_user_id: itineraryForm.assignedPlannerUserId || null,
      urban_speed_mph_override: parseOptionalSpeed(itineraryForm.urbanSpeedOverride),
      highway_speed_mph_override: parseOptionalSpeed(itineraryForm.highwaySpeedOverride)
    });
    await loadProjectWorkspace();
    await selectItinerary(itinerary.id);
  } catch (err) {
    setActionError(err, "Failed to create itinerary");
  } finally {
    savingItinerary.value = false;
  }
}

async function updateSelectedItinerary() {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  savingItinerary.value = true;
  error.value = null;
  try {
    await plannerApi.updateItinerary(selectedProjectId.value, selectedItinerary.value.id, {
      name: itineraryForm.name,
      description: itineraryForm.description,
      status: itineraryForm.status,
      assigned_planner_user_id: itineraryForm.assignedPlannerUserId || null,
      urban_speed_mph_override: parseOptionalSpeed(itineraryForm.urbanSpeedOverride),
      highway_speed_mph_override: parseOptionalSpeed(itineraryForm.highwaySpeedOverride)
    });
    await refreshSelectedItinerary();
  } catch (err) {
    setActionError(err, "Failed to update itinerary");
  } finally {
    savingItinerary.value = false;
  }
}

async function archiveSelectedItinerary() {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  savingItinerary.value = true;
  error.value = null;
  try {
    await plannerApi.archiveItinerary(selectedProjectId.value, selectedItinerary.value.id);
    await loadProjectWorkspace();
  } catch (err) {
    setActionError(err, "Failed to archive itinerary");
  } finally {
    savingItinerary.value = false;
  }
}

function onImportFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0] ?? null;
  selectedImportFile.value = file;
}

function onSyncPackageFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedSyncPackageFile.value = target.files?.[0] ?? null;
}

async function exportSelectedItinerary(format: "csv" | "xlsx") {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  exportingFormat.value = format;
  error.value = null;
  try {
    const { blob, fileName } = await plannerApi.exportItinerary(selectedProjectId.value, selectedItinerary.value.id, format);
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(objectUrl);
  } catch (err) {
    setActionError(err, "Failed to export itinerary file");
  } finally {
    exportingFormat.value = null;
  }
}

async function importIntoSelectedItinerary() {
  if (!selectedProjectId.value || !selectedItinerary.value || !selectedImportFile.value) return;
  importingItinerary.value = true;
  error.value = null;
  try {
    const receipt = await plannerApi.importItinerary(
      selectedProjectId.value,
      selectedItinerary.value.id,
      selectedImportFile.value
    );
    if (receipt.applied) {
      await refreshSelectedItinerary();
    }
    importReceipt.value = receipt;
    selectedImportFile.value = null;
  } catch (err) {
    setActionError(err, "Failed to import itinerary file");
  } finally {
    importingItinerary.value = false;
  }
}

async function exportSelectedProjectSyncPackage() {
  if (!selectedProjectId.value) return;
  exportingSyncPackage.value = true;
  error.value = null;
  try {
    const { blob, fileName } = await plannerApi.exportSyncPackage(selectedProjectId.value);
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(objectUrl);
  } catch (err) {
    setActionError(err, "Failed to export sync package");
  } finally {
    exportingSyncPackage.value = false;
  }
}

async function importProjectSyncPackage() {
  if (!selectedProjectId.value || !selectedSyncPackageFile.value) return;
  importingSyncPackage.value = true;
  error.value = null;
  try {
    syncPackageReceipt.value = await plannerApi.importSyncPackage(selectedProjectId.value, selectedSyncPackageFile.value);
    selectedSyncPackageFile.value = null;
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
    if (selectedItinerary.value) {
      await refreshSelectedItinerary();
    }
  } catch (err) {
    setActionError(err, "Failed to import sync package");
  } finally {
    importingSyncPackage.value = false;
  }
}

async function addDay() {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  const parsedDayNumber = Number(dayForm.dayNumber);
  if (!Number.isInteger(parsedDayNumber) || parsedDayNumber < 1) {
    error.value = "Day number must be a positive integer.";
    return;
  }

  try {
    const updated = await plannerApi.createDay(selectedProjectId.value, selectedItinerary.value.id, {
      day_number: parsedDayNumber,
      title: dayForm.title
    });
    selectedItinerary.value = updated;
    hydrateItineraryForm(updated);
    for (const day of updated.days) {
      ensureStopForm(day);
    }
    versions.value = await plannerApi.listVersions(selectedProjectId.value, updated.id);
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
  } catch (err) {
    setActionError(err, "Failed to add itinerary day");
  }
}

async function updateDay(day: ItineraryDay, payload: Record<string, unknown>) {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  try {
    setDaySaveState(day.id, "saving");
    const updated = await plannerApi.updateDay(selectedProjectId.value, selectedItinerary.value.id, day.id, payload);
    selectedItinerary.value = updated;
    versions.value = await plannerApi.listVersions(selectedProjectId.value, updated.id);
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
    for (const row of updated.days) {
      ensureStopForm(row);
    }
    setDaySaveState(day.id, "saved");
  } catch (err) {
    setActionError(err, "Failed to update day");
    setDaySaveState(day.id, "error");
  }
}

async function deleteDay(day: ItineraryDay) {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  try {
    setDaySaveState(day.id, "saving");
    const updated = await plannerApi.deleteDay(selectedProjectId.value, selectedItinerary.value.id, day.id);
    selectedItinerary.value = updated;
    versions.value = await plannerApi.listVersions(selectedProjectId.value, updated.id);
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
  } catch (err) {
    setActionError(err, "Failed to delete day");
    setDaySaveState(day.id, "error");
  }
}

async function addStop(day: ItineraryDay) {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  const form = stopForms[day.id];
  if (!form?.attractionId) {
    error.value = "Select an attraction before adding a stop.";
    return;
  }
  const start = clockInputToMinutes(form.startClock);
  const duration = Number(form.duration);
  if (start === null) {
    error.value = "Start time must be a valid HH:MM value.";
    return;
  }
  if (!Number.isInteger(duration) || duration < 5 || duration > 720) {
    error.value = "Duration must be an integer between 5 and 720 minutes.";
    return;
  }

  try {
    setDaySaveState(day.id, "saving");
    const updated = await plannerApi.createStop(selectedProjectId.value, selectedItinerary.value.id, day.id, {
      attraction_id: form.attractionId,
      start_minute_of_day: start,
      duration_minutes: duration,
      notes: form.notes
    });
    selectedItinerary.value = updated;
    versions.value = await plannerApi.listVersions(selectedProjectId.value, updated.id);
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
    for (const row of updated.days) {
      ensureStopForm(row);
    }
    setDaySaveState(day.id, "saved");
  } catch (err) {
    setActionError(err, "Failed to add stop");
    setDaySaveState(day.id, "error");
  }
}

async function updateStop(day: ItineraryDay, stopId: string, payload: Record<string, unknown>) {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  try {
    setDaySaveState(day.id, "saving");
    const updated = await plannerApi.updateStop(selectedProjectId.value, selectedItinerary.value.id, day.id, stopId, payload);
    selectedItinerary.value = updated;
    versions.value = await plannerApi.listVersions(selectedProjectId.value, updated.id);
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
    setDaySaveState(day.id, "saved");
  } catch (err) {
    setActionError(err, "Failed to save stop changes");
    setDaySaveState(day.id, "error");
  }
}

async function deleteStop(day: ItineraryDay, stopId: string) {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  try {
    setDaySaveState(day.id, "saving");
    const updated = await plannerApi.deleteStop(selectedProjectId.value, selectedItinerary.value.id, day.id, stopId);
    selectedItinerary.value = updated;
    versions.value = await plannerApi.listVersions(selectedProjectId.value, updated.id);
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
    setDaySaveState(day.id, "saved");
  } catch (err) {
    setActionError(err, "Failed to delete stop");
    setDaySaveState(day.id, "error");
  }
}

function handleStopTimeChange(day: ItineraryDay, stopId: string, value: string) {
  const next = clockInputToMinutes(value);
  if (next !== null) {
    void updateStop(day, stopId, { start_minute_of_day: next });
  }
}

function handleStopDurationChange(day: ItineraryDay, stopId: string, value: string) {
  const duration = Number(value);
  if (Number.isInteger(duration) && duration >= 5 && duration <= 720) {
    void updateStop(day, stopId, { duration_minutes: duration });
  }
}

function onStopDragStart(dayId: string, stopId: string) {
  draggingStopByDay.value[dayId] = stopId;
}

function onStopDragEnd(dayId: string) {
  draggingStopByDay.value[dayId] = null;
}

async function onStopDrop(day: ItineraryDay, targetStopId: string) {
  if (!selectedProjectId.value || !selectedItinerary.value) return;
  const sourceStopId = draggingStopByDay.value[day.id];
  if (!sourceStopId || sourceStopId === targetStopId) return;

  const dayInState = selectedItinerary.value.days.find((row) => row.id === day.id);
  if (!dayInState) return;

  const previousStops = [...dayInState.stops];
  const reordered = reorderIds(dayInState.stops, sourceStopId, targetStopId).map((stop, index) => ({
    ...stop,
    order_index: index
  }));
  dayInState.stops = reordered;

  setDaySaveState(day.id, "saving");
  try {
    const updated = await plannerApi.reorderStops(
      selectedProjectId.value,
      selectedItinerary.value.id,
      day.id,
      reordered.map((stop) => stop.id)
    );
    selectedItinerary.value = updated;
    versions.value = await plannerApi.listVersions(selectedProjectId.value, updated.id);
    itineraries.value = await plannerApi.listItineraries(selectedProjectId.value);
    setDaySaveState(day.id, "saved");
  } catch (err) {
    dayInState.stops = previousStops;
    setActionError(err, "Failed to persist stop order");
    setDaySaveState(day.id, "error");
  } finally {
    draggingStopByDay.value[day.id] = null;
  }
}

onMounted(loadProjects);
</script>

<template>
  <div>
    <h2>Planner</h2>
    <p class="muted-inline">Project-scoped itinerary planning with day/stop autosave, travel estimates, and warnings.</p>

    <p v-if="error" class="error-banner">{{ error }}</p>

    <section class="panel stack">
      <label>
        Project
        <select v-model="selectedProjectId" data-testid="planner-project-select" @change="loadProjectWorkspace">
          <option value="" disabled>Select planner project</option>
          <option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }} ({{ project.code }})
          </option>
        </select>
      </label>
      <p v-if="selectedProject" class="muted-inline">
        Access: {{ canEditSelectedProject ? "editable" : "read-only" }}
      </p>
      <p v-if="loadingProjects || loadingWorkspace">Loading planner workspace...</p>
    </section>

    <div class="planner-grid section-gap" v-if="selectedProjectId">
      <section class="panel stack">
        <h3>{{ selectedItinerary ? "Edit itinerary" : "Create itinerary" }}</h3>
        <label>
          Name
          <input
            v-model="itineraryForm.name"
            data-testid="planner-itinerary-name-input"
            :disabled="!canEditSelectedProject || plannerFormLocked"
            required
          />
        </label>
        <label>
          Description
          <textarea v-model="itineraryForm.description" rows="3" :disabled="!canEditSelectedProject || plannerFormLocked" />
        </label>
        <label>
          Status
          <select v-model="itineraryForm.status" :disabled="!canEditSelectedProject || plannerFormLocked">
            <option value="draft">draft</option>
            <option value="active">active</option>
            <option value="archived">archived</option>
          </select>
        </label>
        <label>
          Assigned planner
          <select v-model="itineraryForm.assignedPlannerUserId" :disabled="!canEditSelectedProject || plannerFormLocked">
            <option value="">Unassigned</option>
            <option v-for="planner in plannerUsers" :key="planner.id" :value="planner.id">{{ planner.username }}</option>
          </select>
        </label>
        <div class="fields-grid">
          <label>
            Itinerary urban speed (mph)
            <input
              v-model="itineraryForm.urbanSpeedOverride"
              type="number"
              min="1"
              step="0.1"
              :disabled="!canEditSelectedProject || plannerFormLocked"
            />
          </label>
          <label>
            Itinerary highway speed (mph)
            <input
              v-model="itineraryForm.highwaySpeedOverride"
              type="number"
              min="1"
              step="0.1"
              :disabled="!canEditSelectedProject || plannerFormLocked"
            />
          </label>
        </div>

        <div class="actions-row">
          <button
            v-if="!selectedItinerary"
            class="btn"
            data-testid="planner-itinerary-create-btn"
            :disabled="!canEditSelectedProject || savingItinerary || plannerFormLocked"
            @click="createItineraryFromForm"
          >
            {{ savingItinerary ? "Saving..." : "Create itinerary" }}
          </button>
          <template v-else>
            <button class="btn" :disabled="!canEditSelectedProject || savingItinerary || plannerFormLocked" @click="updateSelectedItinerary">
              {{ savingItinerary ? "Saving..." : "Save itinerary" }}
            </button>
            <button
              class="btn btn-secondary"
              :disabled="!canEditSelectedProject || savingItinerary || plannerFormLocked"
              @click="archiveSelectedItinerary"
            >
              Archive itinerary
            </button>
          </template>
        </div>

        <h4 class="section-gap">Project itineraries</h4>
        <ul class="list-items" v-if="itineraries.length">
          <li v-for="itinerary in itineraries" :key="itinerary.id" class="list-item" data-testid="planner-itinerary-item">
            <div>
              <strong>{{ itinerary.name }}</strong>
              <p class="muted-inline">
                {{ itinerary.status }} • days={{ itinerary.day_count }} • planner={{ itinerary.assigned_planner_username || "none" }}
              </p>
            </div>
            <button class="btn btn-secondary" :disabled="loadingItinerary" @click="selectItinerary(itinerary.id)">Manage</button>
          </li>
        </ul>
        <p v-else>No itineraries yet.</p>
      </section>

      <section class="panel stack" v-if="selectedProjectId">
        <h3>Offline Sync Package</h3>
        <p class="muted-inline">
          Export a portable project sync package for offline transfer, then import on another device. Imports enforce
          checksum integrity and fast-forward conflict rules.
        </p>

        <div class="actions-row">
          <button
            class="btn"
            data-testid="planner-sync-export-btn"
            :disabled="exportingSyncPackage"
            @click="exportSelectedProjectSyncPackage"
          >
            {{ exportingSyncPackage ? 'Exporting package...' : 'Export sync package' }}
          </button>
        </div>

        <div class="stack">
          <label>
            Import sync package (.zip)
            <input
              data-testid="planner-sync-import-file-input"
              type="file"
              accept=".zip"
              :disabled="!canEditSelectedProject || importingSyncPackage"
              @change="onSyncPackageFileChange"
            />
          </label>
          <button
            class="btn"
            data-testid="planner-sync-import-submit-btn"
            :disabled="!canEditSelectedProject || importingSyncPackage || !selectedSyncPackageFile"
            @click="importProjectSyncPackage"
          >
            {{ importingSyncPackage ? 'Importing package...' : 'Import sync package' }}
          </button>
        </div>

        <article v-if="syncPackageReceipt" class="planner-import-receipt" data-testid="planner-sync-receipt">
          <h4>Latest sync import result</h4>
          <p class="muted-inline">
            {{ syncPackageReceipt.file_name }} • integrity={{ syncPackageReceipt.integrity_validated ? 'ok' : 'failed' }}
            • applied={{ syncPackageReceipt.applied_record_count }} • inserted={{ syncPackageReceipt.inserted_record_count }}
            • updated={{ syncPackageReceipt.updated_record_count }} • conflicts={{ syncPackageReceipt.conflict_count }}
            • rejected={{ syncPackageReceipt.rejected_record_count }}
          </p>

          <ul v-if="syncPackageReceipt.file_errors.length" class="warning-list">
            <li v-for="fileError in syncPackageReceipt.file_errors" :key="fileError" data-testid="planner-sync-file-error">
              {{ fileError }}
            </li>
          </ul>

          <ul v-if="syncPackageReceipt.record_results.length" class="list-items section-gap">
            <li
              v-for="result in syncPackageReceipt.record_results"
              :key="`${result.entity_id}-${result.action}-${result.base_version}-${result.target_version}`"
              class="list-item"
              data-testid="planner-sync-result-row"
            >
              <div>
                <strong>
                  {{ result.entity_name || result.entity_id }} — {{ result.action }}
                </strong>
                <p class="muted-inline" data-testid="planner-sync-result-message">
                  base={{ result.base_version }} → target={{ result.target_version }}
                  <span v-if="result.destination_version !== null"> • destination={{ result.destination_version }}</span>
                  • {{ result.message }}
                </p>
              </div>
            </li>
          </ul>
        </article>
      </section>

      <section class="panel stack" v-if="selectedProjectId">
        <h3>Resource Center</h3>
        <p class="muted-inline">
          Upload controlled images/documents for attraction and itinerary scopes. Allowed: PDF, DOCX, XLSX, CSV, JPG, PNG (max 20 MB).
        </p>

        <div class="resource-center-grid">
          <article class="stack">
            <h4>Attraction assets</h4>
            <label>
              Attraction scope
              <select
                v-model="selectedResourceAttractionId"
                data-testid="planner-resource-attraction-select"
                :disabled="resourceCenterLocked"
                @change="onResourceAttractionScopeChange"
              >
                <option value="" disabled>Select attraction</option>
                <option v-for="attraction in catalogAttractions" :key="attraction.id" :value="attraction.id">
                  {{ attraction.name }} ({{ attraction.dataset_name }})
                </option>
              </select>
            </label>

            <label>
              Upload file
              <input
                ref="attractionAssetInputRef"
                data-testid="planner-resource-attraction-file-input"
                type="file"
                accept=".pdf,.docx,.xlsx,.csv,.jpg,.png"
                :disabled="!canEditSelectedProject || resourceCenterLocked || uploadingAttractionAsset"
                @input="onAttractionAssetFileChange"
                @change="onAttractionAssetFileChange"
              />
            </label>
            <button
              class="btn"
              data-testid="planner-resource-attraction-upload-btn"
              :disabled="!canEditSelectedProject || resourceCenterLocked || uploadingAttractionAsset || !attractionUploadReady"
              @click="uploadAttractionAsset"
            >
              {{ uploadingAttractionAsset ? `Uploading ${attractionUploadProgress}%...` : 'Upload attraction asset' }}
            </button>
            <p v-if="uploadingAttractionAsset || attractionUploadProgress" class="muted-inline" data-testid="planner-resource-attraction-progress">
              Upload progress: {{ attractionUploadProgress }}%
            </p>
            <p v-if="lastAttractionUploadValidation" class="muted-inline" data-testid="planner-resource-attraction-validation">
              Server validation: detected={{ lastAttractionUploadValidation.detected_mime_type }} •
              size={{ formatBytes(Number(lastAttractionUploadValidation.size_bytes)) }} •
              checksum={{ lastAttractionUploadValidation.checksum }}
            </p>

            <p v-if="loadingResourceAssets">Loading assets...</p>
            <ul v-else-if="attractionAssets.length" class="resource-asset-grid">
              <li
                v-for="asset in attractionAssets"
                :key="asset.id"
                class="resource-asset-card"
                data-testid="planner-resource-attraction-asset"
              >
                <img
                  v-if="asset.preview_kind === 'image'"
                  class="resource-thumbnail"
                  :src="resourceCenterApi.assetDownloadUrl(selectedProjectId, asset.id)"
                  :alt="asset.original_file_name"
                />
                <div v-else class="resource-document-preview">{{ asset.file_extension.toUpperCase() }}</div>
                <div>
                  <strong>{{ asset.original_file_name }}</strong>
                  <p class="muted-inline">{{ asset.detected_mime_type }} • {{ formatBytes(asset.file_size_bytes) }}</p>
                  <a
                    class="resource-download-link"
                    :href="resourceCenterApi.assetDownloadUrl(selectedProjectId, asset.id)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open
                  </a>
                </div>
                <button class="btn btn-secondary" :disabled="!canEditSelectedProject || resourceCenterLocked" @click="unreferenceAsset(asset)">Unreference</button>
              </li>
            </ul>
            <p v-else class="muted-inline">No attraction assets yet.</p>
          </article>

          <article class="stack" v-if="activeResourceItineraryId()">
            <h4>Itinerary assets</h4>
            <p class="muted-inline">Scope: {{ activeResourceItineraryName() }}</p>
            <label>
              Upload file
              <input
                ref="itineraryAssetInputRef"
                data-testid="planner-resource-itinerary-file-input"
                type="file"
                accept=".pdf,.docx,.xlsx,.csv,.jpg,.png"
                :disabled="!canEditSelectedProject || resourceCenterLocked || uploadingItineraryAsset"
                @input="onItineraryAssetFileChange"
                @change="onItineraryAssetFileChange"
              />
            </label>
            <button
              class="btn"
              data-testid="planner-resource-itinerary-upload-btn"
              :disabled="!canEditSelectedProject || resourceCenterLocked || uploadingItineraryAsset || !itineraryUploadReady"
              @click="uploadItineraryAsset"
            >
              {{ uploadingItineraryAsset ? `Uploading ${itineraryUploadProgress}%...` : 'Upload itinerary asset' }}
            </button>
            <p v-if="uploadingItineraryAsset || itineraryUploadProgress" class="muted-inline" data-testid="planner-resource-itinerary-progress">
              Upload progress: {{ itineraryUploadProgress }}%
            </p>
            <p v-if="lastItineraryUploadValidation" class="muted-inline" data-testid="planner-resource-itinerary-validation">
              Server validation: detected={{ lastItineraryUploadValidation.detected_mime_type }} •
              size={{ formatBytes(Number(lastItineraryUploadValidation.size_bytes)) }} •
              checksum={{ lastItineraryUploadValidation.checksum }}
            </p>

            <ul v-if="itineraryAssets.length" class="resource-asset-grid">
              <li
                v-for="asset in itineraryAssets"
                :key="asset.id"
                class="resource-asset-card"
                data-testid="planner-resource-itinerary-asset"
              >
                <img
                  v-if="asset.preview_kind === 'image'"
                  class="resource-thumbnail"
                  :src="resourceCenterApi.assetDownloadUrl(selectedProjectId, asset.id)"
                  :alt="asset.original_file_name"
                />
                <div v-else class="resource-document-preview">{{ asset.file_extension.toUpperCase() }}</div>
                <div>
                  <strong>{{ asset.original_file_name }}</strong>
                  <p class="muted-inline">{{ asset.detected_mime_type }} • {{ formatBytes(asset.file_size_bytes) }}</p>
                  <a
                    class="resource-download-link"
                    :href="resourceCenterApi.assetDownloadUrl(selectedProjectId, asset.id)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open
                  </a>
                </div>
                <button class="btn btn-secondary" :disabled="!canEditSelectedProject || resourceCenterLocked" @click="unreferenceAsset(asset)">Unreference</button>
              </li>
            </ul>
            <p v-else class="muted-inline">No itinerary assets yet.</p>
          </article>
        </div>
      </section>

      <section class="panel stack" v-if="selectedItinerary">
        <h3>Days and stops</h3>
        <p class="muted-inline">
          Org defaults: urban {{ selectedItinerary.org_default_urban_speed_mph }} mph, highway
          {{ selectedItinerary.org_default_highway_speed_mph }} mph.
        </p>

        <div class="actions-row">
          <input v-model="dayForm.dayNumber" type="number" min="1" placeholder="Day number" :disabled="!canEditSelectedProject" />
          <input v-model="dayForm.title" placeholder="Day title" :disabled="!canEditSelectedProject" />
          <button class="btn" data-testid="planner-day-add-btn" :disabled="!canEditSelectedProject" @click="addDay">Add day</button>
        </div>

        <article v-for="day in selectedItinerary.days" :key="day.id" class="planner-day-card" data-testid="planner-day-card">
          <header class="actions-row">
            <h4>Day {{ day.day_number }} — {{ day.title || "Untitled" }}</h4>
            <span class="chip save-state-chip" data-testid="planner-day-save-state">{{ daySaveStateLabel(day.id) }}</span>
            <button class="btn btn-secondary" :disabled="!canEditSelectedProject" @click="deleteDay(day)">Delete day</button>
          </header>

          <p class="muted-inline">
            Effective speeds: urban {{ day.effective_urban_speed_mph }} mph / highway {{ day.effective_highway_speed_mph }} mph
          </p>
          <p class="muted-inline">
            Estimated travel: {{ day.travel_distance_miles }} miles, {{ day.travel_time_minutes }} minutes
          </p>
          <p class="muted-inline">Activity duration: {{ day.activity_minutes }} minutes</p>

          <ul class="warning-list" v-if="day.warnings.length">
            <li v-for="warning in day.warnings" :key="`${day.id}-${warning.code}-${warning.message}`" data-testid="planner-warning">
              {{ warning.message }}
            </li>
          </ul>

          <div class="fields-grid section-gap">
            <label>
              Day title
              <input :value="day.title ?? ''" :disabled="!canEditSelectedProject" @change="updateDay(day, { title: ($event.target as HTMLInputElement).value || null })" />
            </label>
            <label>
              Day urban speed (mph)
              <input
                type="number"
                min="1"
                step="0.1"
                :value="day.effective_urban_speed_mph"
                :disabled="!canEditSelectedProject"
                @change="updateDay(day, { urban_speed_mph_override: Number(($event.target as HTMLInputElement).value) || null })"
              />
            </label>
            <label>
              Day highway speed (mph)
              <input
                type="number"
                min="1"
                step="0.1"
                :value="day.effective_highway_speed_mph"
                :disabled="!canEditSelectedProject"
                @change="updateDay(day, { highway_speed_mph_override: Number(($event.target as HTMLInputElement).value) || null })"
              />
            </label>
          </div>

          <div class="actions-row section-gap">
            <select v-model="getStopForm(day).attractionId" :disabled="!canEditSelectedProject">
              <option value="">Select attraction</option>
              <option v-for="attraction in catalogAttractions" :key="attraction.id" :value="attraction.id">
                {{ attraction.name }} ({{ attraction.dataset_name }})
              </option>
            </select>
            <input v-model="getStopForm(day).startClock" type="time" :disabled="!canEditSelectedProject" />
            <input v-model="getStopForm(day).duration" type="number" min="5" max="720" :disabled="!canEditSelectedProject" />
            <button class="btn" :disabled="!canEditSelectedProject" @click="addStop(day)">Add stop</button>
          </div>

          <ul class="planner-stops list-items section-gap">
            <li
              v-for="stop in day.stops"
              :key="stop.id"
              class="list-item planner-stop-row"
              data-testid="planner-stop-row"
              draggable="true"
              @dragstart="onStopDragStart(day.id, stop.id)"
              @dragend="onStopDragEnd(day.id)"
              @dragover.prevent
              @drop.prevent="onStopDrop(day, stop.id)"
            >
              <div class="planner-stop-main">
                <strong>{{ stop.attraction_name }}</strong>
                <p class="muted-inline">{{ stop.attraction_city }}, {{ stop.attraction_state }}</p>
              </div>
              <div class="actions-row">
                <input
                  type="time"
                  :value="minutesToClockInput(stop.start_minute_of_day)"
                  :disabled="!canEditSelectedProject"
                  @change="handleStopTimeChange(day, stop.id, ($event.target as HTMLInputElement).value)"
                />
                <input
                  type="number"
                  min="5"
                  max="720"
                  :value="stop.duration_minutes"
                  :disabled="!canEditSelectedProject"
                  @change="handleStopDurationChange(day, stop.id, ($event.target as HTMLInputElement).value)"
                />
                <button class="btn btn-secondary" :disabled="!canEditSelectedProject" @click="deleteStop(day, stop.id)">
                  Remove
                </button>
              </div>
            </li>
          </ul>
        </article>
      </section>

      <section class="panel stack" v-if="selectedItinerary">
        <h3>Import / Export</h3>
        <p class="muted-inline">Exports include full day/stop rows. Imports replace this itinerary's days/stops using accepted rows.</p>

        <div class="actions-row">
          <button
            class="btn"
            data-testid="planner-export-csv-btn"
            :disabled="exportingFormat !== null"
            @click="exportSelectedItinerary('csv')"
          >
            {{ exportingFormat === 'csv' ? 'Exporting...' : 'Export CSV' }}
          </button>
          <button
            class="btn btn-secondary"
            data-testid="planner-export-xlsx-btn"
            :disabled="exportingFormat !== null"
            @click="exportSelectedItinerary('xlsx')"
          >
            {{ exportingFormat === 'xlsx' ? 'Exporting...' : 'Export XLSX' }}
          </button>
        </div>

        <div class="stack">
          <label>
            Import file (.csv or .xlsx)
            <input
              data-testid="planner-import-file-input"
              type="file"
              accept=".csv,.xlsx"
              :disabled="!canEditSelectedProject || importingItinerary"
              @change="onImportFileChange"
            />
          </label>
          <button
            class="btn"
            data-testid="planner-import-submit-btn"
            :disabled="!canEditSelectedProject || importingItinerary || !selectedImportFile"
            @click="importIntoSelectedItinerary"
          >
            {{ importingItinerary ? 'Importing...' : 'Import into itinerary' }}
          </button>
        </div>

        <article v-if="importReceipt" class="planner-import-receipt" data-testid="planner-import-receipt">
          <h4>Latest import receipt</h4>
          <p class="muted-inline">
            {{ importReceipt.file_name }} • applied={{ importReceipt.applied ? 'yes' : 'no' }} • accepted={{ importReceipt.accepted_row_count }}
            • rejected={{ importReceipt.rejected_row_count }}
          </p>

          <ul v-if="importReceipt.file_errors.length" class="warning-list">
            <li v-for="fileError in importReceipt.file_errors" :key="fileError" data-testid="planner-import-file-error">
              {{ fileError }}
            </li>
          </ul>

          <h5 class="section-gap">Accepted rows</h5>
          <p v-if="!importReceipt.accepted_rows.length" class="muted-inline">No accepted rows.</p>
          <ul v-else class="list-items">
            <li
              v-for="row in importReceipt.accepted_rows"
              :key="`accepted-${row.row_number}`"
              class="list-item"
              data-testid="planner-import-accepted-row"
            >
              <div>
                <strong>Row {{ row.row_number }}</strong>
                <p class="muted-inline">
                  Day {{ row.day_number }} / Stop {{ row.stop_order }} • {{ row.attraction_name }} • {{ row.start_time }} •
                  {{ row.duration_minutes }}m
                </p>
              </div>
            </li>
          </ul>

          <h5 class="section-gap">Rejected rows</h5>
          <p v-if="!importReceipt.rejected_rows.length" class="muted-inline">No rejected rows.</p>
          <ul v-else class="list-items">
            <li
              v-for="row in importReceipt.rejected_rows"
              :key="`rejected-${row.row_number}`"
              class="list-item"
              data-testid="planner-import-rejected-row"
            >
              <div>
                <strong>Row {{ row.row_number }}</strong>
                <ul class="warning-list">
                  <li v-for="errorMessage in row.errors" :key="`error-${row.row_number}-${errorMessage}`">{{ errorMessage }}</li>
                </ul>
                <ul class="muted-inline" v-if="row.correction_hints.length">
                  <li
                    v-for="hint in row.correction_hints"
                    :key="`hint-${row.row_number}-${hint}`"
                    data-testid="planner-import-hint"
                  >
                    Hint: {{ hint }}
                  </li>
                </ul>
              </div>
            </li>
          </ul>
        </article>

        <h3>Version history</h3>
        <ul class="list-items" v-if="versions.length">
          <li v-for="version in versions" :key="version.id" class="list-item" data-testid="planner-version-item">
            <div>
              <strong>v{{ version.version_number }} — {{ version.change_summary }}</strong>
              <p class="muted-inline">{{ version.created_by_username }} • {{ new Date(version.created_at).toLocaleString() }}</p>
            </div>
          </li>
        </ul>
        <p v-else>No versions yet.</p>
      </section>
    </div>
  </div>
</template>
