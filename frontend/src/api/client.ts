export type ApiError = {
  status: number;
  message: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const tokenStorageKey = "workflow_builder_access_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(tokenStorageKey);
}

export function setAccessToken(token: string): void {
  localStorage.setItem(tokenStorageKey, token);
}

export function clearAccessToken(): void {
  localStorage.removeItem(tokenStorageKey);
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw {
      status: response.status,
      message: body?.detail ?? "Request failed",
    } satisfies ApiError;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

