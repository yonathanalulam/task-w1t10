import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";

import WorkspaceShell from "../../src/components/WorkspaceShell.vue";
import { useAuthStore } from "../../src/stores/auth";

const stubView = { template: "<div />" };

function mountShell() {
  const pinia = createPinia();
  setActivePinia(pinia);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", name: "login", component: stubView },
      { path: "/workspace", name: "workspace-overview", component: stubView },
      { path: "/workspace/planner", name: "workspace-planner", component: stubView },
      { path: "/workspace/messages", name: "workspace-message-center", component: stubView },
      { path: "/workspace/datasets", name: "workspace-datasets", component: stubView },
      { path: "/workspace/projects", name: "workspace-projects", component: stubView },
      { path: "/workspace/operations", name: "workspace-operations", component: stubView },
      { path: "/workspace/audit", name: "workspace-audit", component: stubView }
    ]
  });

  const wrapper = mount(WorkspaceShell, {
    global: {
      plugins: [pinia, router]
    }
  });

  return { wrapper };
}

function getLinkTexts(wrapper: ReturnType<typeof mountShell>["wrapper"]) {
  return wrapper.findAll(".nav-link").map((link) => link.text());
}

describe("WorkspaceShell component", () => {
  it("shows ORG_ADMIN-scoped navigation (Overview + Planner + Message Center + governance + Operations)", async () => {
    const { wrapper } = mountShell();
    const store = useAuthStore();
    store.user = {
      id: "user-admin",
      username: "demo-admin",
      org_id: "org-1",
      org_slug: "default-org",
      roles: ["ORG_ADMIN"],
      step_up_valid_until: null
    };
    await wrapper.vm.$nextTick();

    const links = getLinkTexts(wrapper);
    expect(links).toEqual([
      "Overview",
      "Planner",
      "Message Center",
      "Datasets",
      "Projects",
      "Operations"
    ]);

    expect(wrapper.text()).toContain("User: demo-admin");
    expect(wrapper.text()).toContain("Organization: default-org");
    expect(wrapper.find(".role-chip").text()).toBe("ORG_ADMIN");
    expect(wrapper.find('[data-testid="governance-nav-gated-message"]').exists()).toBe(false);
  });

  it("restricts a planner to only Overview, Planner, and Message Center and shows the gated notice", async () => {
    const { wrapper } = mountShell();
    const store = useAuthStore();
    store.user = {
      id: "user-planner",
      username: "demo-planner",
      org_id: "org-1",
      org_slug: "default-org",
      roles: ["PLANNER"],
      step_up_valid_until: null
    };
    await wrapper.vm.$nextTick();

    expect(getLinkTexts(wrapper)).toEqual(["Overview", "Planner", "Message Center"]);
    expect(wrapper.find('[data-testid="governance-nav-gated-message"]').exists()).toBe(true);
  });

  it("shows only the Overview and Audit & Lineage links for an auditor", async () => {
    const { wrapper } = mountShell();
    const store = useAuthStore();
    store.user = {
      id: "user-audit",
      username: "demo-auditor",
      org_id: "org-1",
      org_slug: "default-org",
      roles: ["AUDITOR"],
      step_up_valid_until: null
    };
    await wrapper.vm.$nextTick();

    const links = getLinkTexts(wrapper);
    expect(links).toContain("Overview");
    expect(links.some((text) => text.startsWith("Audit"))).toBe(true);
    expect(links).not.toContain("Datasets");
    expect(links).not.toContain("Projects");
    expect(links).not.toContain("Operations");
    expect(links).not.toContain("Planner");
  });
});
