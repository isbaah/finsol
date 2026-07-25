import { API_BASE_URL } from "@/lib/env";
import { getCsrfToken } from "@/lib/csrf";

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/**
 * Fired whenever a request to our own `/api/v1/...` endpoints comes back
 * 401 — the one reliable, endpoint-agnostic signal that a previously valid
 * session has expired mid-use. Registered by SessionProvider, which has
 * access to the router and the toast system; kept out of this module to
 * keep it framework-shallow and easy to unit test.
 */
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

/**
 * For our own DRF-backed `/api/v1/...` endpoints. Throws ApiError on any
 * non-2xx response — unlike allauth's headless endpoints, a non-2xx here is
 * a genuine error, not a normal flow-control outcome.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  // FormData needs the browser to set its own multipart boundary header —
  // an explicit "application/json" here would silently break file uploads
  // (Stage 9's disbursement evidence upload is the first caller to pass one).
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (UNSAFE_METHODS.has(method)) {
    const token = getCsrfToken();
    if (token) headers.set("X-CSRFToken", token);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  if (response.status === 401) {
    unauthorizedHandler?.();
  }

  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body as T;
}
