import { apiDelete, apiGet, apiGetRaw, apiPatch, apiPost, apiPostForm } from "./client";

export type PlannerProject = {
  id: string;
  name: string;
  code: string;
  can_edit: boolean;
};

export type PlannerUser = {
  id: string;
  username: string;
};

export type PlannerCatalogAttraction = {
  id: string;
  dataset_id: string;
  dataset_name: string;
  name: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  duration_minutes: number;
};

export type ItineraryWarning = {
  code: string;
  message: string;
};

export type ItineraryStop = {
  id: string;
  itinerary_day_id: string;
  attraction_id: string;
  attraction_name: string;
  attraction_city: string;
  attraction_state: string;
  latitude: number;
  longitude: number;
  order_index: number;
  start_minute_of_day: number;
  duration_minutes: number;
  notes: string | null;
};

export type ItineraryDay = {
  id: string;
  itinerary_id: string;
  day_number: number;
  title: string | null;
  notes: string | null;
  effective_urban_speed_mph: number;
  effective_highway_speed_mph: number;
  travel_distance_miles: number;
  travel_time_minutes: number;
  activity_minutes: number;
  warnings: ItineraryWarning[];
  stops: ItineraryStop[];
};

export type Itinerary = {
  id: string;
  org_id: string;
  project_id: string;
  name: string;
  description: string | null;
  status: string;
  assigned_planner_user_id: string | null;
  assigned_planner_username: string | null;
  urban_speed_mph_override: number | null;
  highway_speed_mph_override: number | null;
  org_default_urban_speed_mph: number;
  org_default_highway_speed_mph: number;
  created_at: string;
  updated_at: string;
  version_counter: number;
  days: ItineraryDay[];
};

export type ItineraryListItem = {
  id: string;
  project_id: string;
  name: string;
  status: string;
  assigned_planner_user_id: string | null;
  assigned_planner_username: string | null;
  updated_at: string;
  day_count: number;
};

export type ItineraryVersion = {
  id: string;
  itinerary_id: string;
  version_number: number;
  change_summary: string;
  created_by_user_id: string;
  created_by_username: string;
  created_at: string;
  snapshot: Record<string, unknown>;
};

export type ItineraryImportAcceptedRow = {
  row_number: number;
  day_number: number;
  stop_order: number;
  attraction_id: string;
  attraction_name: string;
  start_time: string;
  duration_minutes: number;
};

export type ItineraryImportRejectedRow = {
  row_number: number;
  raw_row: Record<string, string>;
  errors: string[];
  correction_hints: string[];
};

export type ItineraryImportReceipt = {
  itinerary_id: string;
  project_id: string;
  file_name: string;
  file_format: string;
  imported_at: string;
  applied: boolean;
  total_rows: number;
  accepted_row_count: number;
  rejected_row_count: number;
  applied_day_count: number;
  applied_stop_count: number;
  file_errors: string[];
  accepted_rows: ItineraryImportAcceptedRow[];
  rejected_rows: ItineraryImportRejectedRow[];
};

export type SyncPackageRecordResult = {
  record_type: string;
  entity_id: string;
  entity_name: string;
  action: string;
  base_version: number;
  target_version: number;
  destination_version: number | null;
  message: string;
};

export type SyncPackageImportReceipt = {
  project_id: string;
  file_name: string;
  imported_at: string;
  format_version: string | null;
  integrity_validated: boolean;
  total_record_count: number;
  inserted_record_count: number;
  updated_record_count: number;
  conflict_count: number;
  rejected_record_count: number;
  applied_record_count: number;
  file_errors: string[];
  record_results: SyncPackageRecordResult[];
};

function parseFileNameFromDisposition(disposition: string | null): string | null {
  if (!disposition) return null;
  const match = disposition.match(/filename="([^"]+)"/i);
  return match?.[1] ?? null;
}

export const plannerApi = {
  listPlannerProjects: () => apiGet<PlannerProject[]>("/api/planner/projects"),
  listAssignablePlanners: () => apiGet<PlannerUser[]>("/api/planner/users"),

  listProjectCatalogAttractions: (projectId: string) =>
    apiGet<PlannerCatalogAttraction[]>(`/api/projects/${projectId}/catalog/attractions`),

  listItineraries: (projectId: string) => apiGet<ItineraryListItem[]>(`/api/projects/${projectId}/itineraries`),
  createItinerary: (
    projectId: string,
    payload: {
      name: string;
      description?: string;
      status: string;
      assigned_planner_user_id?: string | null;
      urban_speed_mph_override?: number | null;
      highway_speed_mph_override?: number | null;
    }
  ) => apiPost<Itinerary>(`/api/projects/${projectId}/itineraries`, payload),
  getItinerary: (projectId: string, itineraryId: string) =>
    apiGet<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}`),
  updateItinerary: (projectId: string, itineraryId: string, payload: Record<string, unknown>) =>
    apiPatch<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}`, payload),
  archiveItinerary: (projectId: string, itineraryId: string) =>
    apiDelete<void>(`/api/projects/${projectId}/itineraries/${itineraryId}`),

  createDay: (
    projectId: string,
    itineraryId: string,
    payload: {
      day_number: number;
      title?: string;
      notes?: string;
      urban_speed_mph_override?: number | null;
      highway_speed_mph_override?: number | null;
    }
  ) => apiPost<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}/days`, payload),
  updateDay: (
    projectId: string,
    itineraryId: string,
    dayId: string,
    payload: Record<string, unknown>
  ) => apiPatch<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}/days/${dayId}`, payload),
  deleteDay: (projectId: string, itineraryId: string, dayId: string) =>
    apiDelete<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}/days/${dayId}`),

  createStop: (
    projectId: string,
    itineraryId: string,
    dayId: string,
    payload: {
      attraction_id: string;
      start_minute_of_day: number;
      duration_minutes: number;
      notes?: string;
    }
  ) => apiPost<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}/days/${dayId}/stops`, payload),
  updateStop: (
    projectId: string,
    itineraryId: string,
    dayId: string,
    stopId: string,
    payload: Record<string, unknown>
  ) => apiPatch<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}/days/${dayId}/stops/${stopId}`, payload),
  deleteStop: (projectId: string, itineraryId: string, dayId: string, stopId: string) =>
    apiDelete<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}/days/${dayId}/stops/${stopId}`),
  reorderStops: (projectId: string, itineraryId: string, dayId: string, orderedStopIds: string[]) =>
    apiPost<Itinerary>(`/api/projects/${projectId}/itineraries/${itineraryId}/days/${dayId}/stops/reorder`, {
      ordered_stop_ids: orderedStopIds
    }),

  listVersions: (projectId: string, itineraryId: string) =>
    apiGet<ItineraryVersion[]>(`/api/projects/${projectId}/itineraries/${itineraryId}/versions`),

  exportItinerary: async (projectId: string, itineraryId: string, format: "csv" | "xlsx") => {
    const response = await apiGetRaw(
      `/api/projects/${projectId}/itineraries/${itineraryId}/export?format=${encodeURIComponent(format)}`
    );
    const blob = await response.blob();
    const fileName = parseFileNameFromDisposition(response.headers.get("content-disposition")) ?? `itinerary.${format}`;
    return { blob, fileName };
  },

  importItinerary: (projectId: string, itineraryId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiPostForm<ItineraryImportReceipt>(`/api/projects/${projectId}/itineraries/${itineraryId}/import`, formData);
  },

  exportSyncPackage: async (projectId: string) => {
    const response = await apiGetRaw(`/api/projects/${projectId}/sync-package/export`);
    const blob = await response.blob();
    const fileName = parseFileNameFromDisposition(response.headers.get("content-disposition")) ?? "sync-package.zip";
    return { blob, fileName };
  },

  importSyncPackage: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiPostForm<SyncPackageImportReceipt>(`/api/projects/${projectId}/sync-package/import`, formData);
  }
};
