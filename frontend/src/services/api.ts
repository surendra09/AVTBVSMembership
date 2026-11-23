import axios, { AxiosError, type AxiosRequestConfig } from "axios";

/**
 * Axios instance. Authentication lives in HttpOnly cookies set by the API – the
 * browser never stores tokens in localStorage. For state-changing requests the
 * CSRF cookie value is echoed in the X-CSRF-Token header (double-submit).
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  withCredentials: true,
  timeout: 30000,
});

function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

api.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (!["get", "head", "options"].includes(method)) {
    const token = readCookie("avtbvs_csrf");
    if (token) config.headers.set("X-CSRF-Token", token);
  }
  return config;
});

let refreshing: Promise<boolean> | null = null;
let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(fn: () => void) {
  onSessionExpired = fn;
}

async function refreshSession(): Promise<boolean> {
  try {
    await api.post("/auth/refresh", undefined, { _skipRefresh: true } as AxiosRequestConfig);
    return true;
  } catch {
    return false;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retried?: boolean; _skipRefresh?: boolean }) | undefined;
    const url = original?.url ?? "";
    const isAuthCall = /\/auth\/(login|register|refresh|logout|token)/.test(url);
    if (error.response?.status === 401 && original && !original._retried && !original._skipRefresh && !isAuthCall) {
      original._retried = true;
      refreshing = refreshing ?? refreshSession().finally(() => setTimeout(() => (refreshing = null), 0));
      if (await refreshing) return api(original);
      onSessionExpired?.();
    }
    return Promise.reject(error);
  },
);

export interface ApiErrorInfo {
  message: string;
  fieldErrors: Record<string, string>;
  status?: number;
}

export function parseApiError(err: unknown, fallback = "Something went wrong. Please try again."): ApiErrorInfo {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (!err.response) return { message: "Cannot reach the server. Check your connection and try again.", fieldErrors: {} };
    if (typeof detail === "string") return { message: detail, fieldErrors: {}, status };
    if (detail && typeof detail === "object") {
      const d = detail as { message?: string; errors?: Record<string, string> };
      return { message: d.message ?? fallback, fieldErrors: d.errors ?? {}, status };
    }
    if (status === 413) return { message: "The file is too large.", fieldErrors: {}, status };
    return { message: fallback, fieldErrors: {}, status };
  }
  return { message: fallback, fieldErrors: {} };
}
