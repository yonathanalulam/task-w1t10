import { describe, expect, it } from "vitest";

import { extractTemplateVariables } from "../../src/utils/message-center";

describe("message center template variable extraction", () => {
  it("extracts ordered unique placeholders", () => {
    const body = "Hi {{ traveler_name }}, depart {{departure_time}}. Bye {{traveler_name}}.";
    expect(extractTemplateVariables(body)).toEqual(["traveler_name", "departure_time"]);
  });

  it("returns empty list when no placeholders exist", () => {
    expect(extractTemplateVariables("Static body without variables.")).toEqual([]);
  });
});
