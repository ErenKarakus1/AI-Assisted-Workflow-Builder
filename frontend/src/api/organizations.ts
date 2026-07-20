import { apiRequest } from "./client";
import type { Organization, OrganizationMember } from "../types/api";

export function listOrganizations(): Promise<Organization[]> {
  return apiRequest<Organization[]>("/api/orgs");
}

export function createOrganization(name: string): Promise<Organization> {
  return apiRequest<Organization>("/api/orgs", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listOrganizationMembers(organizationId: string): Promise<OrganizationMember[]> {
  return apiRequest<OrganizationMember[]>(`/api/orgs/${organizationId}/members`);
}

export function addOrganizationMember(
  organizationId: string,
  payload: { email: string; role: "admin" | "member" },
): Promise<OrganizationMember> {
  return apiRequest<OrganizationMember>(`/api/orgs/${organizationId}/members`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function removeOrganizationMember(organizationId: string, memberId: string): Promise<void> {
  return apiRequest<void>(`/api/orgs/${organizationId}/members/${memberId}`, {
    method: "DELETE",
  });
}

export function deleteOrganization(organizationId: string): Promise<void> {
  return apiRequest<void>(`/api/orgs/${organizationId}`, {
    method: "DELETE",
  });
}
