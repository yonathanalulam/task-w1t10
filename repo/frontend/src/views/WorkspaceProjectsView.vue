<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { ApiError } from "../api/client";
import { Dataset, OrgUser, Project, ProjectDatasetLink, ProjectMember, governanceApi } from "../api/governance";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();

const loading = ref(false);
const savingProject = ref(false);
const error = ref<string | null>(null);

const projects = ref<Project[]>([]);
const datasets = ref<Dataset[]>([]);
const orgUsers = ref<OrgUser[]>([]);

const selectedProjectId = ref<string | null>(null);
const projectMembers = ref<ProjectMember[]>([]);
const projectDatasets = ref<ProjectDatasetLink[]>([]);

const projectForm = reactive({
  name: "",
  code: "",
  description: "",
  status: "active"
});

const memberForm = reactive({
  user_id: "",
  role_in_project: "contributor",
  can_edit: true
});

const linkDatasetId = ref("");
const membershipStepUpPassword = ref("");
const membershipStepUpStatus = ref<string | null>(null);
const membershipSteppingUp = ref(false);

const selectedProject = computed(() => projects.value.find((p) => p.id === selectedProjectId.value) ?? null);

function setActionError(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    error.value = err.message;
    return;
  }
  error.value = err instanceof Error ? err.message : fallback;
}

function resetProjectForm() {
  selectedProjectId.value = null;
  projectForm.name = "";
  projectForm.code = "";
  projectForm.description = "";
  projectForm.status = "active";
  projectMembers.value = [];
  projectDatasets.value = [];
}

async function loadAll() {
  loading.value = true;
  error.value = null;
  try {
    const [projectsRes, datasetsRes, usersRes] = await Promise.all([
      governanceApi.listProjects(),
      governanceApi.listDatasets(),
      governanceApi.listOrgUsers()
    ]);
    projects.value = projectsRes;
    datasets.value = datasetsRes;
    orgUsers.value = usersRes;
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      error.value = "You do not have permission to manage projects.";
    } else {
      error.value = err instanceof Error ? err.message : "Failed to load governance data";
    }
  } finally {
    loading.value = false;
  }
}

async function selectProject(project: Project) {
  selectedProjectId.value = project.id;
  projectForm.name = project.name;
  projectForm.code = project.code;
  projectForm.description = project.description ?? "";
  projectForm.status = project.status;

  const [members, links] = await Promise.all([
    governanceApi.listProjectMembers(project.id),
    governanceApi.listProjectDatasets(project.id)
  ]);
  projectMembers.value = members;
  projectDatasets.value = links;
}

async function saveProject() {
  savingProject.value = true;
  error.value = null;
  try {
    if (selectedProjectId.value) {
      await governanceApi.updateProject(selectedProjectId.value, {
        name: projectForm.name,
        code: projectForm.code,
        description: projectForm.description,
        status: projectForm.status
      });
    } else {
      await governanceApi.createProject({
        name: projectForm.name,
        code: projectForm.code,
        description: projectForm.description,
        status: projectForm.status
      });
      resetProjectForm();
    }
    await loadAll();
    if (selectedProjectId.value) {
      const project = projects.value.find((p) => p.id === selectedProjectId.value);
      if (project) {
        await selectProject(project);
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to save project";
  } finally {
    savingProject.value = false;
  }
}

async function addMember() {
  if (!selectedProjectId.value) return;
  error.value = null;
  try {
    await governanceApi.addProjectMember(selectedProjectId.value, {
      user_id: memberForm.user_id,
      role_in_project: memberForm.role_in_project,
      can_edit: memberForm.can_edit
    });
    projectMembers.value = await governanceApi.listProjectMembers(selectedProjectId.value);
    membershipStepUpStatus.value = null;
  } catch (err) {
    if (err instanceof ApiError && err.status === 403 && err.message.includes("Step-up authentication required")) {
      error.value = "Project membership changes require recent password step-up.";
      return;
    }
    setActionError(err, "Failed to add member");
  }
}

async function toggleMemberEdit(member: ProjectMember) {
  if (!selectedProjectId.value) return;
  error.value = null;
  try {
    await governanceApi.updateProjectMember(selectedProjectId.value, member.id, {
      can_edit: !member.can_edit
    });
    projectMembers.value = await governanceApi.listProjectMembers(selectedProjectId.value);
    membershipStepUpStatus.value = null;
  } catch (err) {
    if (err instanceof ApiError && err.status === 403 && err.message.includes("Step-up authentication required")) {
      error.value = "Project membership changes require recent password step-up.";
      return;
    }
    setActionError(err, "Failed to update member");
  }
}

async function removeMember(member: ProjectMember) {
  if (!selectedProjectId.value) return;
  error.value = null;
  try {
    await governanceApi.removeProjectMember(selectedProjectId.value, member.id);
    projectMembers.value = await governanceApi.listProjectMembers(selectedProjectId.value);
    membershipStepUpStatus.value = null;
  } catch (err) {
    if (err instanceof ApiError && err.status === 403 && err.message.includes("Step-up authentication required")) {
      error.value = "Project membership changes require recent password step-up.";
      return;
    }
    setActionError(err, "Failed to remove member");
  }
}

async function verifyMembershipStepUp() {
  if (!membershipStepUpPassword.value.trim()) {
    error.value = "Provide your password to verify step-up for membership changes.";
    return;
  }
  membershipSteppingUp.value = true;
  error.value = null;
  membershipStepUpStatus.value = null;
  try {
    await authStore.stepUp(membershipStepUpPassword.value);
    membershipStepUpStatus.value = "Step-up verified for project membership changes.";
    membershipStepUpPassword.value = "";
  } catch (err) {
    setActionError(err, "Step-up failed");
  } finally {
    membershipSteppingUp.value = false;
  }
}

async function linkDataset() {
  if (!selectedProjectId.value || !linkDatasetId.value) return;
  error.value = null;
  try {
    await governanceApi.linkDatasetToProject(selectedProjectId.value, linkDatasetId.value);
    projectDatasets.value = await governanceApi.listProjectDatasets(selectedProjectId.value);
  } catch (err) {
    setActionError(err, "Failed to link dataset");
  }
}

async function unlinkDataset(datasetId: string) {
  if (!selectedProjectId.value) return;
  error.value = null;
  try {
    await governanceApi.unlinkDatasetFromProject(selectedProjectId.value, datasetId);
    projectDatasets.value = await governanceApi.listProjectDatasets(selectedProjectId.value);
  } catch (err) {
    setActionError(err, "Failed to unlink dataset");
  }
}

onMounted(loadAll);
</script>

<template>
  <div>
    <h2>Projects</h2>
    <p class="muted-inline">Collaboration workspaces with governed members and linked datasets.</p>

    <p v-if="error" class="error-banner">{{ error }}</p>

    <div class="admin-grid">
      <section class="panel">
        <h3>{{ selectedProjectId ? "Edit project" : "Create project" }}</h3>
        <form class="stack" @submit.prevent="saveProject">
          <label>
            Name
            <input v-model="projectForm.name" data-testid="project-name-input" required />
          </label>
          <label>
            Code
            <input v-model="projectForm.code" data-testid="project-code-input" required />
          </label>
          <label>
            Description
            <textarea v-model="projectForm.description" rows="3" />
          </label>
          <label>
            Status
            <select v-model="projectForm.status">
              <option value="active">active</option>
              <option value="archived">archived</option>
            </select>
          </label>
          <div class="actions-row">
            <button class="btn" data-testid="project-save-btn" type="submit" :disabled="savingProject">
              {{ savingProject ? "Saving..." : selectedProjectId ? "Update project" : "Create project" }}
            </button>
            <button class="btn btn-secondary" type="button" @click="resetProjectForm">Clear</button>
          </div>
        </form>

        <h3 class="section-gap">Existing projects</h3>
        <p v-if="loading">Loading projects...</p>
        <ul v-else-if="projects.length" class="list-items">
          <li v-for="project in projects" :key="project.id" class="list-item">
            <div>
              <strong>{{ project.name }}</strong>
              <p class="muted-inline">{{ project.code }} • {{ project.status }}</p>
            </div>
            <button class="btn btn-secondary" @click="selectProject(project)">Manage</button>
          </li>
        </ul>
        <p v-else>No projects yet.</p>
      </section>

      <section class="panel">
        <h3>Project membership</h3>
        <p v-if="!selectedProject">Select a project to manage members and datasets.</p>
        <template v-else>
          <p class="muted-inline">Selected: {{ selectedProject.name }}</p>
          <div class="panel stack section-gap">
            <h4>Step-up for membership & permission changes</h4>
            <label>
              Password
              <input v-model="membershipStepUpPassword" type="password" data-testid="projects-step-up-password-input" />
            </label>
            <button
              class="btn"
              type="button"
              data-testid="projects-step-up-btn"
              :disabled="membershipSteppingUp"
              @click="verifyMembershipStepUp"
            >
              {{ membershipSteppingUp ? "Verifying..." : "Verify step-up" }}
            </button>
            <p v-if="membershipStepUpStatus" class="planner-import-receipt">{{ membershipStepUpStatus }}</p>
          </div>
          <form class="stack" @submit.prevent="addMember">
            <label>
              User
              <select v-model="memberForm.user_id" data-testid="project-member-user-select" required>
                <option value="" disabled>Select org user</option>
                <option v-for="user in orgUsers" :key="user.id" :value="user.id">{{ user.username }}</option>
              </select>
            </label>
            <label>
              Role in project
              <input v-model="memberForm.role_in_project" required />
            </label>
            <label class="checkbox-row">
              <input v-model="memberForm.can_edit" type="checkbox" />
              Editable
            </label>
            <button class="btn" data-testid="project-member-add-btn" type="submit">Add member</button>
          </form>

          <ul class="list-items section-gap" v-if="projectMembers.length">
            <li v-for="member in projectMembers" :key="member.id" class="list-item" data-testid="project-member-item">
              <div>
                <strong>{{ member.username }}</strong>
                <p class="muted-inline">{{ member.role_in_project }} • edit={{ member.can_edit }}</p>
              </div>
              <div class="actions-row">
                <button class="btn btn-secondary" @click="toggleMemberEdit(member)">Toggle edit</button>
                <button class="btn btn-secondary" @click="removeMember(member)">Remove</button>
              </div>
            </li>
          </ul>
          <p v-else class="section-gap">No members added yet.</p>

          <h3 class="section-gap">Linked datasets</h3>
          <div class="actions-row">
            <select v-model="linkDatasetId" data-testid="project-link-dataset-select">
              <option value="">Select dataset to link</option>
              <option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">{{ dataset.name }}</option>
            </select>
            <button class="btn" data-testid="project-link-dataset-btn" type="button" @click="linkDataset">Link</button>
          </div>
          <ul class="list-items section-gap" v-if="projectDatasets.length">
            <li v-for="link in projectDatasets" :key="link.id" class="list-item">
              <strong>{{ link.dataset_name }}</strong>
              <button class="btn btn-secondary" @click="unlinkDataset(link.dataset_id)">Unlink</button>
            </li>
          </ul>
          <p v-else class="section-gap">No linked datasets yet.</p>
        </template>
      </section>
    </div>
  </div>
</template>
