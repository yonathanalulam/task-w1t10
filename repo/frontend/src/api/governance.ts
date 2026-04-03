import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

export type Dataset = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Attraction = {
  id: string;
  dataset_id: string;
  name: string;
  city: string;
  state: string;
  description: string | null;
  latitude: number;
  longitude: number;
  duration_minutes: number;
  status: string;
  normalized_dedupe_key: string;
  merged_into_attraction_id: string | null;
  merged_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AttractionDuplicateGroup = {
  duplicate_key: string;
  duplicate_label: string;
  candidate_count: number;
  candidates: Attraction[];
};

export type AttractionMergeResult = {
  merge_event_id: string;
  source_attraction_id: string;
  target_attraction_id: string;
  merged_at: string;
};

export type Project = {
  id: string;
  name: string;
  code: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type OrgUser = {
  id: string;
  username: string;
  active: boolean;
  roles: string[];
};

export type ProjectMember = {
  id: string;
  user_id: string;
  username: string;
  role_in_project: string;
  can_edit: boolean;
  created_at: string;
  updated_at: string;
};

export type ProjectDatasetLink = {
  id: string;
  dataset_id: string;
  dataset_name: string;
  created_at: string;
};

export const governanceApi = {
  listDatasets: () => apiGet<Dataset[]>("/api/datasets"),
  createDataset: (payload: { name: string; description: string; status: string }) =>
    apiPost<Dataset>("/api/datasets", payload),
  updateDataset: (id: string, payload: Partial<{ name: string; description: string; status: string }>) =>
    apiPatch<Dataset>(`/api/datasets/${id}`, payload),

  listProjects: () => apiGet<Project[]>("/api/projects"),
  createProject: (payload: { name: string; code: string; description: string; status: string }) =>
    apiPost<Project>("/api/projects", payload),
  updateProject: (id: string, payload: Partial<{ name: string; code: string; description: string; status: string }>) =>
    apiPatch<Project>(`/api/projects/${id}`, payload),

  listOrgUsers: () => apiGet<OrgUser[]>("/api/admin/users"),

  listAttractions: (datasetId: string) => apiGet<Attraction[]>(`/api/datasets/${datasetId}/attractions`),
  createAttraction: (
    datasetId: string,
    payload: {
      name: string;
      city: string;
      state: string;
      description: string;
      latitude: number;
      longitude: number;
      duration_minutes: number;
      status: string;
    }
  ) => apiPost<Attraction>(`/api/datasets/${datasetId}/attractions`, payload),
  updateAttraction: (
    datasetId: string,
    attractionId: string,
    payload: Partial<{
      name: string;
      city: string;
      state: string;
      description: string;
      latitude: number;
      longitude: number;
      duration_minutes: number;
      status: string;
    }>
  ) => apiPatch<Attraction>(`/api/datasets/${datasetId}/attractions/${attractionId}`, payload),
  listAttractionDuplicates: (datasetId: string) =>
    apiGet<AttractionDuplicateGroup[]>(`/api/datasets/${datasetId}/attractions/duplicates`),
  mergeAttractions: (
    datasetId: string,
    payload: {
      source_attraction_id: string;
      target_attraction_id: string;
      merge_reason?: string;
    }
  ) => apiPost<AttractionMergeResult>(`/api/datasets/${datasetId}/attractions/merge`, payload),

  listProjectMembers: (projectId: string) => apiGet<ProjectMember[]>(`/api/projects/${projectId}/members`),
  addProjectMember: (projectId: string, payload: { user_id: string; role_in_project: string; can_edit: boolean }) =>
    apiPost<ProjectMember>(`/api/projects/${projectId}/members`, payload),
  updateProjectMember: (
    projectId: string,
    memberId: string,
    payload: Partial<{ role_in_project: string; can_edit: boolean }>
  ) => apiPatch<ProjectMember>(`/api/projects/${projectId}/members/${memberId}`, payload),
  removeProjectMember: (projectId: string, memberId: string) =>
    apiDelete<void>(`/api/projects/${projectId}/members/${memberId}`),

  listProjectDatasets: (projectId: string) => apiGet<ProjectDatasetLink[]>(`/api/projects/${projectId}/datasets`),
  linkDatasetToProject: (projectId: string, datasetId: string) =>
    apiPost<ProjectDatasetLink>(`/api/projects/${projectId}/datasets/${datasetId}`, {}),
  unlinkDatasetFromProject: (projectId: string, datasetId: string) =>
    apiDelete<void>(`/api/projects/${projectId}/datasets/${datasetId}`)
};
