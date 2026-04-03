<script setup lang="ts">
import { computed, watch } from "vue";
import { useRouter } from "vue-router";

import WorkspaceShell from "../components/WorkspaceShell.vue";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();

const showAuthBootstrapLoading = computed(() => authStore.bootstrapping && !authStore.isAuthenticated);

watch(
  () => [authStore.bootstrapping, authStore.initialized, authStore.isAuthenticated] as const,
  async ([bootstrapping, initialized, isAuthenticated]) => {
    if (!bootstrapping && initialized && !isAuthenticated) {
      await router.replace({ name: "login" });
    }
  },
  { immediate: true }
);
</script>

<template>
  <section v-if="showAuthBootstrapLoading" class="workspace-auth-loading" data-testid="workspace-auth-loading">
    <div class="card">
      <h2>Loading workspace…</h2>
      <p class="muted-inline">Checking your session and permissions.</p>
    </div>
  </section>
  <WorkspaceShell v-else />
</template>
