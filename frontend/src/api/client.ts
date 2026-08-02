import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "./schema";

const TOKEN_KEY = "retail_token";

let token: string | null = localStorage.getItem(TOKEN_KEY);
let onUnauthorized: (() => void) | null = null;

export function getToken(): string | null {
  return token;
}

export function setToken(next: string | null): void {
  token = next;
  if (next) localStorage.setItem(TOKEN_KEY, next);
  else localStorage.removeItem(TOKEN_KEY);
}

/** Registered once by AuthProvider so a 401 anywhere logs the user out. */
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

const authMiddleware: Middleware = {
  onRequest({ request }) {
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ response }) {
    if (response.status === 401) onUnauthorized?.();
    return response;
  },
};

// baseUrl "/" — every path in the generated schema already starts with
// "/api/...". The Vite dev server proxies /api to the backend (vite.config.ts)
// and nginx does the same in production, so the frontend never needs to know
// the API's origin.
export const api = createClient<paths>({ baseUrl: "/" });
api.use(authMiddleware);

/** Extracts a FastAPI-style `{detail: "..."}` message, falling back to the
 * status code — mirrors the old app's error handling in a typed form. */
export function apiErrorMessage(error: unknown, fallback = "Ошибка запроса"): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

/** Triggers a browser download for an authenticated file endpoint (CSV/XLSX
 * exports, document downloads) that isn't part of the typed JSON API. */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(path, { headers });
  if (!res.ok) throw new Error(`Не удалось скачать файл (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
