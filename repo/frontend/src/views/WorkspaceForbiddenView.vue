<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const requestedPath = computed(() => {
  const queryFrom = route.query.from;
  return typeof queryFrom === "string" ? queryFrom : null;
});
</script>

<template>
  <div>
    <h2>Restricted surface</h2>
    <p>This route requires additional planner or organization-admin access.</p>
    <p v-if="requestedPath" class="muted-inline">Requested route: {{ requestedPath }}</p>
    <p class="muted-inline">If you need access, contact your organization administrator.</p>
  </div>
</template>
