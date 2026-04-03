import { createRouter, createWebHistory } from "vue-router";

import LoginView from "../views/LoginView.vue";
import WorkspaceView from "../views/WorkspaceView.vue";
import WorkspaceOverviewView from "../views/WorkspaceOverviewView.vue";
import WorkspaceDatasetsView from "../views/WorkspaceDatasetsView.vue";
import WorkspaceProjectsView from "../views/WorkspaceProjectsView.vue";
import WorkspacePlannerView from "../views/WorkspacePlannerView.vue";
import WorkspaceMessageCenterView from "../views/WorkspaceMessageCenterView.vue";
import WorkspaceOperationsView from "../views/WorkspaceOperationsView.vue";
import WorkspaceForbiddenView from "../views/WorkspaceForbiddenView.vue";
import { useAuthStore } from "../stores/auth";
import { resolveRouteAccess } from "./access";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/workspace"
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: "/workspace",
      name: "workspace",
      component: WorkspaceView,
      meta: { requiresAuth: true },
      redirect: { name: "workspace-overview" },
      children: [
        {
          path: "overview",
          name: "workspace-overview",
          component: WorkspaceOverviewView,
          meta: { requiresAuth: true }
        },
        {
          path: "datasets",
          name: "workspace-datasets",
          component: WorkspaceDatasetsView,
          meta: { requiresAuth: true, requiresOrgAdmin: true }
        },
        {
          path: "projects",
          name: "workspace-projects",
          component: WorkspaceProjectsView,
          meta: { requiresAuth: true, requiresOrgAdmin: true }
        },
        {
          path: "planner",
          name: "workspace-planner",
          component: WorkspacePlannerView,
          meta: { requiresAuth: true, requiresPlannerAccess: true }
        },
        {
          path: "messages",
          name: "workspace-message-center",
          component: WorkspaceMessageCenterView,
          meta: { requiresAuth: true, requiresPlannerAccess: true }
        },
        {
          path: "operations",
          name: "workspace-operations",
          component: WorkspaceOperationsView,
          meta: { requiresAuth: true, requiresOrgAdmin: true }
        },
        {
          path: "audit",
          name: "workspace-audit",
          component: WorkspaceOperationsView,
          props: { readOnly: true },
          meta: { requiresAuth: true, requiresAuditAccess: true }
        },
        {
          path: "forbidden",
          name: "workspace-forbidden",
          component: WorkspaceForbiddenView,
          meta: { requiresAuth: true }
        }
      ]
    }
  ]
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore();
  await authStore.bootstrap();

  return resolveRouteAccess(to, {
    isAuthenticated: authStore.isAuthenticated,
    isOrgAdmin: authStore.isOrgAdmin,
    canAudit: authStore.canAudit,
    isPlanner: authStore.isPlanner
  });
});
