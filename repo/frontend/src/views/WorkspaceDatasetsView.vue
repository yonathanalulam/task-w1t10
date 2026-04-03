<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { ApiError } from "../api/client";
import { Attraction, AttractionDuplicateGroup, Dataset, governanceApi } from "../api/governance";
import { useAuthStore } from "../stores/auth";
import { validateAttractionDraft } from "../utils/attractions";

const authStore = useAuthStore();

const loadingDatasets = ref(false);
const savingDataset = ref(false);
const loadingAttractions = ref(false);
const savingAttraction = ref(false);
const error = ref<string | null>(null);

const datasets = ref<Dataset[]>([]);
const attractions = ref<Attraction[]>([]);
const duplicateGroups = ref<AttractionDuplicateGroup[]>([]);

const selectedDatasetId = ref<string | null>(null);
const selectedAttractionId = ref<string | null>(null);

const datasetForm = reactive({
  name: "",
  description: "",
  status: "active"
});

const attractionForm = reactive({
  name: "",
  city: "",
  state: "",
  description: "",
  latitude: "",
  longitude: "",
  durationMinutes: "60",
  status: "active"
});

const duplicateMergeSelections = reactive<Record<string, { sourceId: string; targetId: string }>>({});
const mergeStepUpPassword = ref("");
const mergeStepUpStatus = ref<string | null>(null);
const mergeSteppingUp = ref(false);

const selectedDataset = computed(() => datasets.value.find((dataset) => dataset.id === selectedDatasetId.value) ?? null);

function setActionError(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    error.value = err.message;
    return;
  }
  error.value = err instanceof Error ? err.message : fallback;
}

function resetDatasetForm() {
  selectedDatasetId.value = null;
  datasetForm.name = "";
  datasetForm.description = "";
  datasetForm.status = "active";
  resetAttractionForm();
  attractions.value = [];
  duplicateGroups.value = [];
}

function resetAttractionForm() {
  selectedAttractionId.value = null;
  attractionForm.name = "";
  attractionForm.city = "";
  attractionForm.state = "";
  attractionForm.description = "";
  attractionForm.latitude = "";
  attractionForm.longitude = "";
  attractionForm.durationMinutes = "60";
  attractionForm.status = "active";
}

function hydrateDuplicateSelections(groups: AttractionDuplicateGroup[]) {
  for (const key of Object.keys(duplicateMergeSelections)) {
    delete duplicateMergeSelections[key];
  }

  for (const group of groups) {
    if (group.candidates.length < 2) continue;
    duplicateMergeSelections[group.duplicate_key] = {
      targetId: group.candidates[0].id,
      sourceId: group.candidates[1].id
    };
  }
}

async function loadDatasets() {
  loadingDatasets.value = true;
  error.value = null;
  try {
    datasets.value = await governanceApi.listDatasets();
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      error.value = "You do not have permission to manage datasets.";
    } else {
      error.value = err instanceof Error ? err.message : "Failed to load datasets";
    }
  } finally {
    loadingDatasets.value = false;
  }
}

async function loadDatasetAttractions(datasetId: string) {
  loadingAttractions.value = true;
  try {
    const [attractionsRes, duplicatesRes] = await Promise.all([
      governanceApi.listAttractions(datasetId),
      governanceApi.listAttractionDuplicates(datasetId)
    ]);
    attractions.value = attractionsRes;
    duplicateGroups.value = duplicatesRes;
    hydrateDuplicateSelections(duplicatesRes);
  } catch (err) {
    setActionError(err, "Failed to load attraction catalog");
  } finally {
    loadingAttractions.value = false;
  }
}

async function selectDataset(dataset: Dataset) {
  selectedDatasetId.value = dataset.id;
  datasetForm.name = dataset.name;
  datasetForm.description = dataset.description ?? "";
  datasetForm.status = dataset.status;
  resetAttractionForm();
  await loadDatasetAttractions(dataset.id);
}

function selectAttraction(attraction: Attraction) {
  selectedAttractionId.value = attraction.id;
  attractionForm.name = attraction.name;
  attractionForm.city = attraction.city;
  attractionForm.state = attraction.state;
  attractionForm.description = attraction.description ?? "";
  attractionForm.latitude = String(attraction.latitude);
  attractionForm.longitude = String(attraction.longitude);
  attractionForm.durationMinutes = String(attraction.duration_minutes);
  attractionForm.status = attraction.status;
}

async function submitDataset() {
  savingDataset.value = true;
  error.value = null;
  try {
    if (selectedDatasetId.value) {
      await governanceApi.updateDataset(selectedDatasetId.value, {
        name: datasetForm.name,
        description: datasetForm.description,
        status: datasetForm.status
      });
    } else {
      await governanceApi.createDataset({
        name: datasetForm.name,
        description: datasetForm.description,
        status: datasetForm.status
      });
      resetDatasetForm();
    }
    await loadDatasets();
    if (selectedDatasetId.value) {
      const current = datasets.value.find((dataset) => dataset.id === selectedDatasetId.value);
      if (current) {
        await selectDataset(current);
      }
    }
  } catch (err) {
    setActionError(err, "Failed to save dataset");
  } finally {
    savingDataset.value = false;
  }
}

async function submitAttraction() {
  if (!selectedDatasetId.value) {
    error.value = "Select a dataset before managing attractions.";
    return;
  }

  const validationError = validateAttractionDraft({
    name: attractionForm.name,
    city: attractionForm.city,
    state: attractionForm.state,
    latitude: attractionForm.latitude,
    longitude: attractionForm.longitude,
    durationMinutes: attractionForm.durationMinutes
  });
  if (validationError) {
    error.value = validationError;
    return;
  }

  savingAttraction.value = true;
  error.value = null;
  try {
    const payload = {
      name: attractionForm.name,
      city: attractionForm.city,
      state: attractionForm.state,
      description: attractionForm.description,
      latitude: Number(attractionForm.latitude),
      longitude: Number(attractionForm.longitude),
      duration_minutes: Number(attractionForm.durationMinutes),
      status: attractionForm.status
    };

    if (selectedAttractionId.value) {
      await governanceApi.updateAttraction(selectedDatasetId.value, selectedAttractionId.value, payload);
    } else {
      await governanceApi.createAttraction(selectedDatasetId.value, payload);
      resetAttractionForm();
    }

    await loadDatasetAttractions(selectedDatasetId.value);
  } catch (err) {
    setActionError(err, "Failed to save attraction");
  } finally {
    savingAttraction.value = false;
  }
}

async function mergeDuplicateGroup(group: AttractionDuplicateGroup) {
  if (!selectedDatasetId.value) return;

  const selection = duplicateMergeSelections[group.duplicate_key];
  if (!selection?.sourceId || !selection?.targetId) {
    error.value = "Select both source and target attractions to merge.";
    return;
  }
  if (selection.sourceId === selection.targetId) {
    error.value = "Source and target attractions must be different for merge.";
    return;
  }

  error.value = null;
  try {
    await governanceApi.mergeAttractions(selectedDatasetId.value, {
      source_attraction_id: selection.sourceId,
      target_attraction_id: selection.targetId,
      merge_reason: `Duplicate review for key ${group.duplicate_key}`
    });
    mergeStepUpStatus.value = null;
    await loadDatasetAttractions(selectedDatasetId.value);
  } catch (err) {
    if (err instanceof ApiError && err.status === 403 && err.message.includes("Step-up authentication required")) {
      error.value = "Attraction merge requires recent password step-up.";
      return;
    }
    setActionError(err, "Failed to merge attractions");
  }
}

async function verifyMergeStepUp() {
  if (!mergeStepUpPassword.value.trim()) {
    error.value = "Provide your password to verify step-up for attraction merge.";
    return;
  }

  mergeSteppingUp.value = true;
  error.value = null;
  mergeStepUpStatus.value = null;
  try {
    await authStore.stepUp(mergeStepUpPassword.value);
    mergeStepUpStatus.value = "Step-up verified for attraction merge.";
    mergeStepUpPassword.value = "";
  } catch (err) {
    setActionError(err, "Step-up failed");
  } finally {
    mergeSteppingUp.value = false;
  }
}

onMounted(loadDatasets);
</script>

<template>
  <div>
    <h2>Datasets</h2>
    <p class="muted-inline">Governed attraction-catalog containers managed at organization scope.</p>

    <p v-if="error" class="error-banner">{{ error }}</p>

    <div class="admin-grid">
      <section class="panel">
        <h3>{{ selectedDatasetId ? "Edit dataset" : "Create dataset" }}</h3>
        <form class="stack" @submit.prevent="submitDataset">
          <label>
            Name
            <input v-model="datasetForm.name" data-testid="dataset-name-input" required />
          </label>
          <label>
            Description
            <textarea v-model="datasetForm.description" rows="4" />
          </label>
          <label>
            Status
            <select v-model="datasetForm.status">
              <option value="active">active</option>
              <option value="archived">archived</option>
            </select>
          </label>

          <div class="actions-row">
            <button class="btn" data-testid="dataset-save-btn" type="submit" :disabled="savingDataset">
              {{ savingDataset ? "Saving..." : selectedDatasetId ? "Update dataset" : "Create dataset" }}
            </button>
            <button class="btn btn-secondary" type="button" @click="resetDatasetForm">Clear</button>
          </div>
        </form>
      </section>

      <section class="panel">
        <h3>Existing datasets</h3>
        <p v-if="loadingDatasets">Loading datasets...</p>
        <p v-else-if="datasets.length === 0">No datasets yet.</p>
        <ul v-else class="list-items">
          <li v-for="dataset in datasets" :key="dataset.id" class="list-item">
            <div>
              <strong>{{ dataset.name }}</strong>
              <p class="muted-inline">Status: {{ dataset.status }}</p>
            </div>
            <button class="btn btn-secondary" @click="selectDataset(dataset)">Manage</button>
          </li>
        </ul>
      </section>

      <section class="panel panel-span">
        <h3>Attraction catalog</h3>
        <p v-if="!selectedDataset">Select a dataset to manage governed attractions and duplicates.</p>
        <template v-else>
          <p class="muted-inline">Selected dataset: {{ selectedDataset.name }}</p>
          <form class="stack section-gap" @submit.prevent="submitAttraction">
            <div class="fields-grid">
              <label>
                Name
                <input v-model="attractionForm.name" data-testid="attraction-name-input" required />
              </label>
              <label>
                City
                <input v-model="attractionForm.city" data-testid="attraction-city-input" required />
              </label>
              <label>
                State
                <input v-model="attractionForm.state" data-testid="attraction-state-input" required />
              </label>
              <label>
                Latitude
                <input v-model="attractionForm.latitude" data-testid="attraction-latitude-input" type="number" step="any" required />
              </label>
              <label>
                Longitude
                <input
                  v-model="attractionForm.longitude"
                  data-testid="attraction-longitude-input"
                  type="number"
                  step="any"
                  required
                />
              </label>
              <label>
                Duration (minutes)
                <input
                  v-model="attractionForm.durationMinutes"
                  data-testid="attraction-duration-input"
                  type="number"
                  min="5"
                  max="720"
                  required
                />
              </label>
            </div>
            <label>
              Description
              <textarea v-model="attractionForm.description" rows="3" />
            </label>
            <label>
              Status
              <select v-model="attractionForm.status">
                <option value="active">active</option>
                <option value="archived">archived</option>
              </select>
            </label>
            <div class="actions-row">
              <button
                class="btn"
                data-testid="attraction-save-btn"
                type="submit"
                :disabled="savingAttraction"
                @click.prevent="submitAttraction"
              >
                {{ savingAttraction ? "Saving..." : selectedAttractionId ? "Update attraction" : "Create attraction" }}
              </button>
              <button class="btn btn-secondary" type="button" @click="resetAttractionForm">Clear</button>
            </div>
          </form>

          <h4 class="section-gap">Attractions in dataset</h4>
          <p v-if="loadingAttractions">Loading attraction catalog...</p>
          <p v-else-if="!attractions.length">No attractions yet.</p>
          <ul v-else class="list-items" data-testid="attraction-list">
            <li v-for="attraction in attractions" :key="attraction.id" class="list-item" data-testid="attraction-list-item">
              <div>
                <strong>{{ attraction.name }}</strong>
                <p class="muted-inline">
                  {{ attraction.city }}, {{ attraction.state }} • {{ attraction.duration_minutes }}m •
                  {{ attraction.latitude }}, {{ attraction.longitude }}
                </p>
                <p class="muted-inline">
                  Status: {{ attraction.status }}
                  <span v-if="attraction.merged_into_attraction_id"> • merged into {{ attraction.merged_into_attraction_id }}</span>
                </p>
              </div>
              <button
                class="btn btn-secondary"
                :disabled="!!attraction.merged_into_attraction_id"
                @click="selectAttraction(attraction)"
              >
                Manage
              </button>
            </li>
          </ul>

          <h4 class="section-gap">Duplicate review</h4>
          <div class="panel stack section-gap">
            <h5>Step-up for duplicate merge</h5>
            <label>
              Password
              <input v-model="mergeStepUpPassword" type="password" data-testid="datasets-step-up-password-input" />
            </label>
            <button
              class="btn"
              type="button"
              data-testid="datasets-step-up-btn"
              :disabled="mergeSteppingUp"
              @click="verifyMergeStepUp"
            >
              {{ mergeSteppingUp ? "Verifying..." : "Verify step-up" }}
            </button>
            <p v-if="mergeStepUpStatus" class="planner-import-receipt">{{ mergeStepUpStatus }}</p>
          </div>
          <p v-if="!duplicateGroups.length" data-testid="duplicate-groups-empty">No duplicate groups pending review.</p>
          <div v-else class="stack">
            <article
              v-for="(group, groupIndex) in duplicateGroups"
              :key="group.duplicate_key"
              class="panel duplicate-group"
              data-testid="duplicate-group"
            >
              <h5>{{ group.duplicate_label }}</h5>
              <p class="muted-inline">{{ group.candidate_count }} candidates with the same deterministic key.</p>
              <ul class="list-items section-gap">
                <li v-for="candidate in group.candidates" :key="candidate.id" class="list-item">
                  <div>
                    <strong>{{ candidate.name }}</strong>
                    <p class="muted-inline">
                      {{ candidate.city }}, {{ candidate.state }} • {{ candidate.duration_minutes }}m
                    </p>
                  </div>
                  <span class="chip">{{ candidate.id.slice(0, 8) }}</span>
                </li>
              </ul>

              <div class="actions-row section-gap">
                <label>
                  Keep as target
                  <select
                    v-model="duplicateMergeSelections[group.duplicate_key].targetId"
                    :data-testid="`duplicate-target-select-${groupIndex}`"
                  >
                    <option v-for="candidate in group.candidates" :key="`target-${candidate.id}`" :value="candidate.id">
                      {{ candidate.name }} ({{ candidate.id.slice(0, 8) }})
                    </option>
                  </select>
                </label>
                <label>
                  Merge source
                  <select
                    v-model="duplicateMergeSelections[group.duplicate_key].sourceId"
                    :data-testid="`duplicate-source-select-${groupIndex}`"
                  >
                    <option v-for="candidate in group.candidates" :key="`source-${candidate.id}`" :value="candidate.id">
                      {{ candidate.name }} ({{ candidate.id.slice(0, 8) }})
                    </option>
                  </select>
                </label>
                <button
                  class="btn"
                  type="button"
                  :data-testid="`duplicate-merge-btn-${groupIndex}`"
                  @click="mergeDuplicateGroup(group)"
                >
                  Merge
                </button>
              </div>
            </article>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
