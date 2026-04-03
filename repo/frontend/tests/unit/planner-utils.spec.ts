import { describe, expect, it } from "vitest";

import { clockInputToMinutes, minutesToClockInput, reorderIds } from "../../src/utils/planner";

describe("planner utilities", () => {
  it("converts clock input values to minutes", () => {
    expect(clockInputToMinutes("00:00")).toBe(0);
    expect(clockInputToMinutes("09:30")).toBe(570);
    expect(clockInputToMinutes("23:59")).toBe(1439);
    expect(clockInputToMinutes("24:00")).toBeNull();
  });

  it("converts minutes to clamped clock strings", () => {
    expect(minutesToClockInput(15)).toBe("00:15");
    expect(minutesToClockInput(570)).toBe("09:30");
    expect(minutesToClockInput(5000)).toBe("23:59");
  });

  it("reorders ids deterministically", () => {
    const input = [{ id: "a" }, { id: "b" }, { id: "c" }];
    const output = reorderIds(input, "c", "a");
    expect(output.map((item) => item.id)).toEqual(["c", "a", "b"]);
  });
});
