import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";

import LoginView from "../../src/views/LoginView.vue";
import { useAuthStore } from "../../src/stores/auth";

function createHarness() {
  const pinia = createPinia();
  setActivePinia(pinia);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", name: "login", component: { template: "<div />" } },
      { path: "/workspace", name: "workspace", component: { template: "<div>ws</div>" } }
    ]
  });

  const wrapper = mount(LoginView, {
    global: {
      plugins: [pinia, router]
    }
  });

  return { wrapper, router };
}

describe("LoginView component", () => {

  it("renders the sign-in card with organization, username, and password inputs", () => {
    const { wrapper } = createHarness();

    expect(wrapper.find("h1").text()).toBe("TrailForge");
    expect(wrapper.find('input[name="orgSlug"]').exists()).toBe(true);
    expect(wrapper.find('input[name="username"]').exists()).toBe(true);
    expect(wrapper.find('input[name="password"]').exists()).toBe(true);
    expect(wrapper.find('button[type="submit"]').text()).toBe("Sign in");
  });

  it("pre-fills the organization slug with the bootstrap default-org", () => {
    const { wrapper } = createHarness();
    const orgInput = wrapper.find<HTMLInputElement>('input[name="orgSlug"]');
    expect(orgInput.element.value).toBe("default-org");
  });

  it("invokes auth store login and navigates to workspace on success", async () => {
    const { wrapper, router } = createHarness();
    const store = useAuthStore();

    const loginSpy = vi.spyOn(store, "login").mockResolvedValue(undefined);
    const pushSpy = vi.spyOn(router, "push");

    await wrapper.find('input[name="username"]').setValue("demo-admin");
    await wrapper.find('input[name="password"]').setValue("TrailForgeDemo!123");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(loginSpy).toHaveBeenCalledWith("default-org", "demo-admin", "TrailForgeDemo!123");
    expect(pushSpy).toHaveBeenCalledWith({ name: "workspace" });
    expect(wrapper.find(".error").exists()).toBe(false);
  });

  it("surfaces an inline error message when login fails", async () => {
    const { wrapper } = createHarness();
    const store = useAuthStore();
    vi.spyOn(store, "login").mockRejectedValue(new Error("Invalid credentials"));

    await wrapper.find('input[name="username"]').setValue("demo-admin");
    await wrapper.find('input[name="password"]').setValue("wrong");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    const errorEl = wrapper.find(".error");
    expect(errorEl.exists()).toBe(true);
    expect(errorEl.text()).toBe("Invalid credentials");
  });
});
