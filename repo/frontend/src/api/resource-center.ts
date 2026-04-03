import { apiDelete, apiGet, apiPostFormWithProgress } from "./client";

export type ResourceAsset = {
  id: string;
  project_id: string;
  scope_type: "attraction" | "itinerary";
  attraction_id: string | null;
  itinerary_id: string | null;
  original_file_name: string;
  file_extension: string;
  declared_mime_type: string | null;
  detected_mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  preview_kind: "image" | "document";
  is_quarantined: boolean;
  quarantine_reason: string | null;
  scan_status: string;
  cleanup_eligible_at: string | null;
  created_at: string;
};

export type ResourceAssetUploadResult = {
  asset: ResourceAsset;
  validation: {
    extension: string;
    declared_mime_type: string | null;
    detected_mime_type: string;
    size_bytes: number;
    checksum: string;
    signature_valid: boolean;
  };
};

function pathForAssetDownload(projectId: string, assetId: string): string {
  return `/api/projects/${projectId}/resources/assets/${assetId}/download`;
}

export const resourceCenterApi = {
  listAttractionAssets: (projectId: string, attractionId: string) =>
    apiGet<ResourceAsset[]>(`/api/projects/${projectId}/resources/attractions/${attractionId}/assets`),

  uploadAttractionAsset: (projectId: string, attractionId: string, file: File, onProgress: (percent: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiPostFormWithProgress<ResourceAssetUploadResult>(
      `/api/projects/${projectId}/resources/attractions/${attractionId}/assets`,
      formData,
      onProgress
    );
  },

  listItineraryAssets: (projectId: string, itineraryId: string) =>
    apiGet<ResourceAsset[]>(`/api/projects/${projectId}/resources/itineraries/${itineraryId}/assets`),

  uploadItineraryAsset: (projectId: string, itineraryId: string, file: File, onProgress: (percent: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiPostFormWithProgress<ResourceAssetUploadResult>(
      `/api/projects/${projectId}/resources/itineraries/${itineraryId}/assets`,
      formData,
      onProgress
    );
  },

  unreferenceAsset: (projectId: string, assetId: string) => apiDelete<ResourceAsset>(`/api/projects/${projectId}/resources/assets/${assetId}`),

  assetDownloadUrl: pathForAssetDownload
};
