import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useAuthStore } from "../../src/stores/auth";

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("tracks failed bootstrap without throwing", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" }
      })
    );

    const store = useAuthStore();
    await store.bootstrap();

    expect(store.initialized).toBe(true);
    expect(store.isAuthenticated).toBe(false);
  });

  it("computes org-admin capability from roles", () => {
    const store = useAuthStore();

    store.user = {
      id: "user-1",
      username: "planner",
      org_id: "org-1",
      org_slug: "default-org",
      roles: ["PLANNER"],
      step_up_valid_until: null
    };
    expect(store.isOrgAdmin).toBe(false);
    expect(store.isPlanner).toBe(true);

    store.user = {
      id: "user-1",
      username: "planner",
      org_id: "org-1",
      org_slug: "default-org",
      roles: ["PLANNER", "ORG_ADMIN"],
      step_up_valid_until: null
    };
    expect(store.isOrgAdmin).toBe(true);
    expect(store.isPlanner).toBe(true);
  });
});
