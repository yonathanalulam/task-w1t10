<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();

const roleBadges = computed(() => authStore.user?.roles ?? []);

async function signOut() {
  await authStore.logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="workspace-shell">
    <header class="topbar">
      <div>
        <h1>TrailForge Workspace</h1>
        <p class="muted">Organization: {{ authStore.user?.org_slug }}</p>
      </div>
      <div class="topbar-right">
        <span class="chip">User: {{ authStore.user?.username }}</span>
        <button class="btn" @click="signOut">Sign out</button>
      </div>
    </header>

    <main class="layout">
      <aside class="sidebar">
        <h2>Workspace Modules</h2>
        <nav class="nav-links">
          <RouterLink class="nav-link" :to="{ name: 'workspace-overview' }">Overview</RouterLink>
          <RouterLink v-if="authStore.isPlanner" class="nav-link" :to="{ name: 'workspace-planner' }">Planner</RouterLink>
          <RouterLink v-if="authStore.isPlanner" class="nav-link" :to="{ name: 'workspace-message-center' }">Message Center</RouterLink>
          <template v-if="authStore.isOrgAdmin">
            <RouterLink class="nav-link" :to="{ name: 'workspace-datasets' }">Datasets</RouterLink>
            <RouterLink class="nav-link" :to="{ name: 'workspace-projects' }">Projects</RouterLink>
            <RouterLink class="nav-link" :to="{ name: 'workspace-operations' }">Operations</RouterLink>
          </template>
          <RouterLink v-else-if="authStore.canAudit" class="nav-link" :to="{ name: 'workspace-audit' }">
            Audit &amp; Lineage
          </RouterLink>
        </nav>

        <div class="role-section">
          <h3>Active roles</h3>
          <div class="roles">
            <span v-for="role in roleBadges" :key="role" class="role-chip">{{ role }}</span>
          </div>
          <p v-if="!authStore.isOrgAdmin" class="warning-text" data-testid="governance-nav-gated-message">
            Datasets and Projects are restricted to Organization Admin users.
          </p>
        </div>
      </aside>

      <section class="content">
        <RouterView />
      </section>
    </main>
  </div>
</template>
