import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import WorkspaceOverviewView from "../../src/views/WorkspaceOverviewView.vue";

describe("WorkspaceOverviewView component", () => {
  it("renders the governed collaboration overview panel", () => {
    const wrapper = mount(WorkspaceOverviewView);

    expect(wrapper.find("h2").text()).toBe("Governed Collaboration Foundation");
    const body = wrapper.text();
    expect(body).toContain("organization-admin datasets");
    expect(body).toContain("message center");
    expect(body).toContain("encrypted backups");
  });
});
