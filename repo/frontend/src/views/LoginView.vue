<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();

const orgSlug = ref("default-org");
const username = ref("");
const password = ref("");
const localError = ref<string | null>(null);

async function onSubmit() {
  localError.value = null;
  try {
    await authStore.login(orgSlug.value, username.value, password.value);
    await router.push({ name: "workspace" });
  } catch (err) {
    localError.value = err instanceof Error ? err.message : "Login failed";
  }
}
</script>

<template>
  <div class="login-page">
    <form class="card" @submit.prevent="onSubmit">
      <h1>TrailForge</h1>
      <p>Sign in to the offline workspace.</p>

      <label>
        Organization
        <input v-model="orgSlug" name="orgSlug" required />
      </label>

      <label>
        Username
        <input v-model="username" name="username" required autocomplete="username" />
      </label>

      <label>
        Password
        <input v-model="password" name="password" type="password" required autocomplete="current-password" />
      </label>

      <button class="btn" type="submit" :disabled="authStore.loading">
        {{ authStore.loading ? "Signing in..." : "Sign in" }}
      </button>

      <p v-if="localError" class="error">{{ localError }}</p>
    </form>
  </div>
</template>
