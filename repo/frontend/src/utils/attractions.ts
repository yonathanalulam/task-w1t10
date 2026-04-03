export type AttractionDraft = {
  name: string;
  city: string;
  state: string;
  latitude: string | number;
  longitude: string | number;
  durationMinutes: string | number;
};

export function validateAttractionDraft(draft: AttractionDraft): string | null {
  const name = String(draft.name ?? "").trim();
  const city = String(draft.city ?? "").trim();
  const state = String(draft.state ?? "").trim();
  const latitudeRaw = String(draft.latitude ?? "").trim();
  const longitudeRaw = String(draft.longitude ?? "").trim();
  const durationRaw = String(draft.durationMinutes ?? "").trim();

  if (!name) return "Attraction name is required.";
  if (!city) return "City is required.";
  if (!state) return "State is required.";

  if (!latitudeRaw || !longitudeRaw) {
    return "Latitude and longitude are required for planner-ready attractions.";
  }

  const latitude = Number(latitudeRaw);
  const longitude = Number(longitudeRaw);
  if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
    return "Latitude must be a valid value between -90 and 90.";
  }
  if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
    return "Longitude must be a valid value between -180 and 180.";
  }

  const duration = Number(durationRaw);
  if (!Number.isInteger(duration) || duration < 5 || duration > 720) {
    return "Duration must be an integer between 5 and 720 minutes.";
  }

  return null;
}
