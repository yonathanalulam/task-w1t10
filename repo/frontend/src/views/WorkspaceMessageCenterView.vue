<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { ApiError } from "../api/client";
import { MessageDispatch, MessagePreview, MessageTemplate, messageCenterApi } from "../api/message-center";
import { ItineraryListItem, PlannerProject, plannerApi } from "../api/planner";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();

const loading = ref(false);
const savingTemplate = ref(false);
const previewing = ref(false);
const sending = ref(false);
const loadingTimeline = ref(false);
const error = ref<string | null>(null);
const success = ref<string | null>(null);

const projects = ref<PlannerProject[]>([]);
const itineraries = ref<ItineraryListItem[]>([]);
const templates = ref<MessageTemplate[]>([]);
const timeline = ref<MessageDispatch[]>([]);

const selectedProjectId = ref("");
const selectedTemplateId = ref("");
const selectedItineraryId = ref("");
const editingTemplateId = ref<string | null>(null);
const preview = ref<MessagePreview | null>(null);

const templateForm = reactive({
  name: "",
  category: "departure",
  channel: "in_app",
  body_template: "Hi {{traveler_name}}, your departure is scheduled for {{departure_time}}.",
  is_active: true
});

const messageForm = reactive({
  recipient_user_id: "",
  traveler_name: "",
  departure_time: ""
});

const selectedProject = computed(() => projects.value.find((project) => project.id === selectedProjectId.value) ?? null);
const canEditSelectedProject = computed(() => selectedProject.value?.can_edit ?? false);

let projectLoadToken = 0;

function setActionError(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    error.value = err.message;
    return;
  }
  error.value = err instanceof Error ? err.message : fallback;
}

function resetTemplateForm() {
  editingTemplateId.value = null;
  templateForm.name = "";
  templateForm.category = "departure";
  templateForm.channel = "in_app";
  templateForm.body_template = "Hi {{traveler_name}}, your departure is scheduled for {{departure_time}}.";
  templateForm.is_active = true;
}

function hydrateTemplateForm(template: MessageTemplate) {
  editingTemplateId.value = template.id;
  templateForm.name = template.name;
  templateForm.category = template.category;
  templateForm.channel = template.channel;
  templateForm.body_template = template.body_template;
  templateForm.is_active = template.is_active;
}

function selectTemplate(templateId: string) {
  selectedTemplateId.value = templateId;
  preview.value = null;
  error.value = null;
  success.value = null;
}

function variablesPayload(): Record<string, string> {
  return {
    traveler_name: messageForm.traveler_name,
    departure_time: messageForm.departure_time,
    sender_username: authStore.user?.username ?? ""
  };
}

async function loadProjectWorkspace() {
  if (!selectedProjectId.value) return;
  const token = ++projectLoadToken;
  loading.value = true;
  error.value = null;
  success.value = null;
  preview.value = null;

  try {
    const [itineraryRows, templateRows] = await Promise.all([
      plannerApi.listItineraries(selectedProjectId.value),
      messageCenterApi.listTemplates(selectedProjectId.value)
    ]);

    if (token !== projectLoadToken) return;
    itineraries.value = itineraryRows;
    templates.value = templateRows;

    if (!templateRows.some((template) => template.id === selectedTemplateId.value)) {
      selectedTemplateId.value = templateRows[0]?.id ?? "";
    }

    if (editingTemplateId.value) {
      const edited = templateRows.find((template) => template.id === editingTemplateId.value);
      if (!edited) {
        resetTemplateForm();
      }
    }

    await loadTimeline(token);
  } catch (err) {
    if (token !== projectLoadToken) return;
    setActionError(err, "Failed to load message center workspace");
  } finally {
    if (token !== projectLoadToken) return;
    loading.value = false;
  }
}

async function loadTimeline(token?: number) {
  if (!selectedProjectId.value) return;
  loadingTimeline.value = true;
  try {
    const rows = await messageCenterApi.listTimeline(selectedProjectId.value, 100);
    if (token && token !== projectLoadToken) return;
    timeline.value = rows;
  } catch (err) {
    if (token && token !== projectLoadToken) return;
    setActionError(err, "Failed to load message timeline");
  } finally {
    if (token && token !== projectLoadToken) return;
    loadingTimeline.value = false;
  }
}

async function loadProjects() {
  loading.value = true;
  error.value = null;
  try {
    const rows = await plannerApi.listPlannerProjects();
    projects.value = rows;
    if (!selectedProjectId.value && rows.length > 0) {
      selectedProjectId.value = rows[0].id;
      await loadProjectWorkspace();
    }
  } catch (err) {
    setActionError(err, "Failed to load planner projects");
  } finally {
    loading.value = false;
  }
}

async function saveTemplate() {
  if (!selectedProjectId.value) return;
  savingTemplate.value = true;
  error.value = null;
  success.value = null;

  try {
    const payload = {
      name: templateForm.name,
      category: templateForm.category,
      channel: templateForm.channel,
      body_template: templateForm.body_template,
      is_active: templateForm.is_active
    };

    const saved = editingTemplateId.value
      ? await messageCenterApi.updateTemplate(selectedProjectId.value, editingTemplateId.value, payload)
      : await messageCenterApi.createTemplate(selectedProjectId.value, payload);

    success.value = editingTemplateId.value ? "Template updated." : "Template created.";
    selectedTemplateId.value = saved.id;
    editingTemplateId.value = saved.id;
    await loadProjectWorkspace();
  } catch (err) {
    setActionError(err, "Failed to save template");
  } finally {
    savingTemplate.value = false;
  }
}

async function previewMessage() {
  if (!selectedProjectId.value || !selectedTemplateId.value) {
    error.value = "Select a template before previewing.";
    return;
  }

  previewing.value = true;
  error.value = null;
  success.value = null;

  try {
    preview.value = await messageCenterApi.preview(selectedProjectId.value, {
      template_id: selectedTemplateId.value,
      itinerary_id: selectedItineraryId.value || null,
      variables: variablesPayload()
    });
  } catch (err) {
    preview.value = null;
    setActionError(err, "Failed to render preview");
  } finally {
    previewing.value = false;
  }
}

async function sendMessage() {
  if (!selectedProjectId.value || !selectedTemplateId.value) {
    error.value = "Select a project and template before sending.";
    return;
  }

  sending.value = true;
  error.value = null;
  success.value = null;

  try {
    const sent = await messageCenterApi.send(selectedProjectId.value, {
      template_id: selectedTemplateId.value,
      recipient_user_id: messageForm.recipient_user_id,
      itinerary_id: selectedItineraryId.value || null,
      variables: variablesPayload()
    });
    success.value = `Message ${sent.send_status === "sent" ? "sent" : "recorded"} via ${sent.channel}.`;
    await loadTimeline();
  } catch (err) {
    setActionError(err, "Failed to send message");
  } finally {
    sending.value = false;
  }
}

onMounted(loadProjects);
</script>

<template>
  <div>
    <h2>Message Center</h2>
    <p class="muted-inline">
      Reusable notification templates with real variable preview, in-app sends, delivery-attempt timeline, and cap
      enforcement.
    </p>

    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-if="success" class="planner-import-receipt">{{ success }}</p>

    <section class="panel stack">
      <label>
        Project
        <select v-model="selectedProjectId" data-testid="message-project-select" @change="loadProjectWorkspace">
          <option value="" disabled>Select planner project</option>
          <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }} ({{ project.code }})</option>
        </select>
      </label>
      <p v-if="selectedProject" class="muted-inline">Access: {{ canEditSelectedProject ? "editable" : "read-only" }}</p>
      <p v-if="loading">Loading message center...</p>
    </section>

    <div v-if="selectedProjectId" class="planner-grid section-gap">
      <section class="panel stack">
        <h3>{{ editingTemplateId ? "Edit template" : "Create template" }}</h3>
        <label>
          Name
          <input v-model="templateForm.name" data-testid="message-template-name-input" :disabled="!canEditSelectedProject || savingTemplate" />
        </label>
        <label>
          Category
          <input
            v-model="templateForm.category"
            data-testid="message-template-category-input"
            :disabled="!canEditSelectedProject || savingTemplate"
          />
        </label>
        <label>
          Channel
          <select
            v-model="templateForm.channel"
            data-testid="message-template-channel-select"
            :disabled="!canEditSelectedProject || savingTemplate"
          >
            <option value="in_app">in_app</option>
            <option value="sms">sms</option>
            <option value="email">email</option>
            <option value="push">push</option>
          </select>
        </label>
        <label class="checkbox-row">
          <input v-model="templateForm.is_active" type="checkbox" :disabled="!canEditSelectedProject || savingTemplate" />
          Active
        </label>
        <label>
          Template body
          <textarea
            v-model="templateForm.body_template"
            data-testid="message-template-body-input"
            rows="6"
            :disabled="!canEditSelectedProject || savingTemplate"
          />
        </label>
        <div class="actions-row">
          <button
            class="btn"
            data-testid="message-template-save-btn"
            :disabled="!canEditSelectedProject || savingTemplate"
            @click="saveTemplate"
          >
            {{ savingTemplate ? "Saving..." : editingTemplateId ? "Update template" : "Create template" }}
          </button>
          <button class="btn btn-secondary" :disabled="savingTemplate" @click="resetTemplateForm">Clear</button>
        </div>

        <h4 class="section-gap">Templates</h4>
        <ul v-if="templates.length" class="list-items">
          <li v-for="template in templates" :key="template.id" class="list-item" data-testid="message-template-item">
            <div>
              <strong>{{ template.name }}</strong>
              <p class="muted-inline">{{ template.category }} • {{ template.channel }} • active={{ template.is_active }}</p>
              <p class="muted-inline">variables: {{ template.variables.join(", ") || "none" }}</p>
            </div>
            <div class="actions-row">
              <button class="btn btn-secondary" @click="selectTemplate(template.id)">Use</button>
              <button class="btn btn-secondary" @click="hydrateTemplateForm(template)">Edit</button>
            </div>
          </li>
        </ul>
        <p v-else class="muted-inline">No templates yet.</p>
      </section>

      <section class="panel stack">
        <h3>Draft + Send</h3>
        <label>
          Template
          <select v-model="selectedTemplateId" data-testid="message-template-select">
            <option value="" disabled>Select template</option>
            <option v-for="template in templates" :key="template.id" :value="template.id">
              {{ template.name }} ({{ template.category }})
            </option>
          </select>
        </label>
        <label>
          Optional itinerary scope
          <select v-model="selectedItineraryId" data-testid="message-itinerary-select">
            <option value="">No itinerary scope</option>
            <option v-for="itinerary in itineraries" :key="itinerary.id" :value="itinerary.id">{{ itinerary.name }}</option>
          </select>
        </label>
        <label>
          Recipient user id
          <input v-model="messageForm.recipient_user_id" data-testid="message-recipient-input" />
        </label>
        <div class="fields-grid">
          <label>
            Traveler name
            <input v-model="messageForm.traveler_name" data-testid="message-traveler-name-input" />
          </label>
          <label>
            Departure time
            <input v-model="messageForm.departure_time" data-testid="message-departure-time-input" placeholder="09:30" />
          </label>
        </div>

        <div class="actions-row">
          <button class="btn btn-secondary" data-testid="message-preview-btn" :disabled="previewing" @click="previewMessage">
            {{ previewing ? "Rendering..." : "Preview render" }}
          </button>
          <button class="btn" data-testid="message-send-btn" :disabled="!canEditSelectedProject || sending" @click="sendMessage">
            {{ sending ? "Sending..." : "Send message" }}
          </button>
        </div>

        <article v-if="preview" class="planner-import-receipt" data-testid="message-preview-output">
          <h4>Preview</h4>
          <p class="muted-inline">{{ preview.rendered_body || "(empty)" }}</p>
          <p v-if="preview.missing_variables.length" class="warning-text">
            Missing variables: {{ preview.missing_variables.join(", ") }}
          </p>
        </article>
      </section>

      <section class="panel stack">
        <h3>Delivery Timeline</h3>
        <p v-if="loadingTimeline">Loading timeline...</p>
        <ul v-else-if="timeline.length" class="list-items">
          <li v-for="row in timeline" :key="row.id" class="list-item message-timeline-item" data-testid="message-timeline-item">
            <div class="stack" style="width: 100%">
              <p class="muted-inline">
                {{ row.created_at }} • {{ row.template_name }} ({{ row.template_category }}) • {{ row.send_status }} •
                recipient={{ row.recipient_user_id }}
              </p>
              <p>{{ row.rendered_body }}</p>
              <ul class="list-items">
                <li
                  v-for="attempt in row.attempts"
                  :key="attempt.id"
                  class="list-item message-attempt-item"
                  data-testid="message-timeline-attempt"
                >
                  <div>
                    <strong>{{ attempt.connector_key }} — {{ attempt.attempt_status }}</strong>
                    <p class="muted-inline">{{ attempt.attempted_at }} • {{ attempt.detail }}</p>
                  </div>
                </li>
              </ul>
            </div>
          </li>
        </ul>
        <p v-else class="muted-inline">No messages sent yet.</p>
      </section>
    </div>
  </div>
</template>
