import { describe, expect, it } from "vitest";

import { resolveRouteAccess } from "../../src/router/access";

describe("resolveRouteAccess", () => {
  const unauth = {
    isAuthenticated: false,
    isOrgAdmin: false,
    canAudit: false,
    isPlanner: false
  };

  const auditor = {
    isAuthenticated: true,
    isOrgAdmin: false,
    canAudit: true,
    isPlanner: false
  };

  const admin = {
    isAuthenticated: true,
    isOrgAdmin: true,
    canAudit: true,
    isPlanner: true
  };

  it("blocks unauthenticated access to auth-required route", () => {
    const decision = resolveRouteAccess(
      {
        name: "workspace-audit",
        fullPath: "/workspace/audit",
        meta: { requiresAuth: true, requiresAuditAccess: true }
      },
      unauth
    );
    expect(decision).toEqual({ name: "login" });
  });

  it("allows auditor into audit route", () => {
    const decision = resolveRouteAccess(
      {
        name: "workspace-audit",
        fullPath: "/workspace/audit",
        meta: { requiresAuth: true, requiresAuditAccess: true }
      },
      auditor
    );
    expect(decision).toBe(true);
  });

  it("blocks auditor from org-admin only governance route", () => {
    const decision = resolveRouteAccess(
      {
        name: "workspace-projects",
        fullPath: "/workspace/projects",
        meta: { requiresAuth: true, requiresOrgAdmin: true }
      },
      auditor
    );
    expect(decision).toEqual({
      name: "workspace-forbidden",
      query: { from: "/workspace/projects" }
    });
  });

  it("allows org admin to operations route", () => {
    const decision = resolveRouteAccess(
      {
        name: "workspace-operations",
        fullPath: "/workspace/operations",
        meta: { requiresAuth: true, requiresOrgAdmin: true }
      },
      admin
    );
    expect(decision).toBe(true);
  });
});
