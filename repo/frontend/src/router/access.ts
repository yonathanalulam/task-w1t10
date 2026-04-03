export type RouteMetaLike = Record<string, unknown>;

export type RouteLike = {
  name?: string | symbol | null;
  fullPath?: string;
  meta?: RouteMetaLike;
  matched?: Array<{
    meta?: RouteMetaLike;
  }>;
};

export type RouteAuthState = {
  isAuthenticated: boolean;
  isOrgAdmin: boolean;
  canAudit: boolean;
  isPlanner: boolean;
};

type RedirectTarget = {
  name: string;
  query?: Record<string, string>;
};

export type RouteAccessDecision = true | RedirectTarget;

function hasMetaFlag(route: RouteLike, flag: string): boolean {
  if (route.meta?.[flag] === true) {
    return true;
  }
  return route.matched?.some((record) => record.meta?.[flag] === true) ?? false;
}

export function resolveRouteAccess(route: RouteLike, auth: RouteAuthState): RouteAccessDecision {
  const requiresAuth = hasMetaFlag(route, "requiresAuth");
  const requiresOrgAdmin = hasMetaFlag(route, "requiresOrgAdmin");
  const requiresAuditAccess = hasMetaFlag(route, "requiresAuditAccess");
  const requiresPlannerAccess = hasMetaFlag(route, "requiresPlannerAccess");

  if (requiresAuth && !auth.isAuthenticated) {
    return { name: "login" };
  }

  if (route.name === "login" && auth.isAuthenticated) {
    return { name: "workspace" };
  }

  if (requiresOrgAdmin && !auth.isOrgAdmin) {
    return {
      name: "workspace-forbidden",
      query: { from: route.fullPath ?? "/workspace" }
    };
  }

  if (requiresPlannerAccess && !auth.isPlanner) {
    return {
      name: "workspace-forbidden",
      query: { from: route.fullPath ?? "/workspace" }
    };
  }

  if (requiresAuditAccess && !auth.canAudit) {
    return {
      name: "workspace-forbidden",
      query: { from: route.fullPath ?? "/workspace" }
    };
  }

  return true;
}
