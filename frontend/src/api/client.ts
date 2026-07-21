import type { TokenPair } from "../types/api";

export type ApiError = {
  status: number;
  message: string;
};

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const accessTokenStorageKey = "workflow_builder_access_token";
const refreshTokenStorageKey = "workflow_builder_refresh_token";

let refreshPromise: Promise<string> | null = null;

export function getAccessToken(): string | null {
  return localStorage.getItem(accessTokenStorageKey);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(refreshTokenStorageKey);
}

export function setTokens(tokens: TokenPair): void {
  localStorage.setItem(accessTokenStorageKey, tokens.access_token);
  localStorage.setItem(refreshTokenStorageKey, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(accessTokenStorageKey);
  localStorage.removeItem(refreshTokenStorageKey);
}

async function parseError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => null);

  return {
    status: response.status,
    message: body?.detail ?? "Request failed",
  };
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    clearTokens();

    throw {
      status: 401,
      message: "Your session has expired",
    } satisfies ApiError;
  }

  const response = await fetch(`${apiBaseUrl}/api/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      refresh_token: refreshToken,
    }),
  });

  if (!response.ok) {
    clearTokens();
    throw await parseError(response);
  }

  const tokens = (await response.json()) as TokenPair;
  setTokens(tokens);

  return tokens.access_token;
}

async function getRefreshedAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function sendRequest(
  path: string,
  options: RequestInit,
  accessToken: string | null,
): Promise<Response> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers,
  });
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const accessToken = getAccessToken();

  let response = await sendRequest(path, options, accessToken);

  if (response.status === 401 && accessToken && getRefreshToken()) {
    try {
      const refreshedAccessToken = await getRefreshedAccessToken();
      response = await sendRequest(path, options, refreshedAccessToken);
    } catch (error) {
      clearTokens();
      throw error;
    }
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}