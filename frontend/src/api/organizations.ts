import { apiRequest } from "./client";
import type { Organization } from "../types/api";

export function listOrganizations(): Promise<Organization[]> {
  return apiRequest<Organization[]>("/api/orgs");
}

export function createOrganization(name: string): Promise<Organization> {
  return apiRequest<Organization>("/api/orgs", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

