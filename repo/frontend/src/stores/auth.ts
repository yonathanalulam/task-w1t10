import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { ApiError, apiGet, apiPost } from "../api/client";

export type AuthUser = {
  id: string;
  username: string;
  org_id: string;
  org_slug: string;
  roles: string[];
  step_up_valid_until: string | null;
};

type AuthResponse = {
  user: AuthUser;
};

export const useAuthStore = defineStore("auth", () => {
  const user = ref<AuthUser | null>(null);
  const loading = ref(false);
  const initialized = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!user.value);
  const isOrgAdmin = computed(() => user.value?.roles.includes("ORG_ADMIN") ?? false);
  const isAuditor = computed(() => user.value?.roles.includes("AUDITOR") ?? false);
  const canAudit = computed(() => isOrgAdmin.value || isAuditor.value);
  const isPlanner = computed(
    () => (user.value?.roles.includes("PLANNER") ?? false) || (user.value?.roles.includes("ORG_ADMIN") ?? false)
  );

  async function bootstrap(): Promise<void> {
    loading.value = true;
    try {
      const response = await apiGet<AuthResponse>("/api/auth/me");
      user.value = response.user;
      error.value = null;
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        user.value = null;
      }
      error.value = null;
    } finally {
      loading.value = false;
      initialized.value = true;
    }
  }

  async function login(orgSlug: string, username: string, password: string): Promise<void> {
    loading.value = true;
    try {
      const response = await apiPost<AuthResponse>("/api/auth/login", {
        org_slug: orgSlug,
        username,
        password
      });
      user.value = response.user;
      error.value = null;
      initialized.value = true;
    } catch (err) {
      user.value = null;
      error.value = err instanceof Error ? err.message : "Login failed";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function logout(): Promise<void> {
    try {
      await apiPost<void>("/api/auth/logout", {});
    } finally {
      user.value = null;
    }
  }

  async function stepUp(password: string): Promise<void> {
    const response = await apiPost<AuthResponse>("/api/auth/step-up", { password });
    user.value = response.user;
  }

  return {
    user,
    loading,
    initialized,
    error,
    isAuthenticated,
    isOrgAdmin,
    isAuditor,
    canAudit,
    isPlanner,
    bootstrap,
    login,
    logout,
    stepUp
  };
});
