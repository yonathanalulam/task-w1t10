import { describe, expect, it } from "vitest";

import { validateAttractionDraft } from "../../src/utils/attractions";

describe("attraction draft validation", () => {
  it("requires planner coordinates", () => {
    const result = validateAttractionDraft({
      name: "Museum",
      city: "Austin",
      state: "TX",
      latitude: "",
      longitude: "",
      durationMinutes: "90"
    });

    expect(result).toBe("Latitude and longitude are required for planner-ready attractions.");
  });

  it("enforces duration range", () => {
    const result = validateAttractionDraft({
      name: "Museum",
      city: "Austin",
      state: "TX",
      latitude: "30.2672",
      longitude: "-97.7431",
      durationMinutes: "721"
    });

    expect(result).toBe("Duration must be an integer between 5 and 720 minutes.");
  });

  it("accepts valid attraction draft", () => {
    const result = validateAttractionDraft({
      name: "Museum",
      city: "Austin",
      state: "TX",
      latitude: "30.2672",
      longitude: "-97.7431",
      durationMinutes: "120"
    });

    expect(result).toBeNull();
  });
});
