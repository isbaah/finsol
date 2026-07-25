import { API_BASE_URL } from "@/lib/env";
import { getCsrfToken } from "@/lib/csrf";

import type { AllauthEnvelope } from "./types";

const HEADLESS_BASE = `${API_BASE_URL}/_allauth/browser/v1`;

/**
 * django-allauth headless endpoints use 200/401/400/409 as normal,
 * meaningful flow-control outcomes (see the envelope shape in types.ts) —
 * unlike our own DRF endpoints, a non-2xx here is not necessarily an
 * "error" the caller should throw on. Only a genuine 5xx or network failure
 * is exceptional.
 */
async function allauthFetch(path: string, init: RequestInit = {}): Promise<AllauthEnvelope> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (method !== "GET") {
    const token = getCsrfToken();
    if (token) headers.set("X-CSRFToken", token);
  }

  const response = await fetch(`${HEADLESS_BASE}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  const body = (await response.json()) as AllauthEnvelope;

  if (response.status >= 500) {
    throw new Error(`Unexpected server error (${response.status})`);
  }
  return body;
}

export function getSession() {
  return allauthFetch("/auth/session");
}

export function signup(email: string, password: string) {
  return allauthFetch("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string) {
  return allauthFetch("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function logout() {
  return allauthFetch("/auth/session", { method: "DELETE" });
}

export function verifyEmail(key: string) {
  return allauthFetch("/auth/email/verify", { method: "POST", body: JSON.stringify({ key }) });
}

export function requestPasswordReset(email: string) {
  return allauthFetch("/auth/password/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(key: string, password: string) {
  return allauthFetch("/auth/password/reset", {
    method: "POST",
    body: JSON.stringify({ key, password }),
  });
}

/** Full-page-navigation URL for the Google sign-in form — see
 * GoogleSignInButton for why this is a real <form> submit, not a fetch()
 * call: RedirectToProviderView expects a form-encoded POST and returns an
 * HTTP redirect the browser must follow to accounts.google.com. */
export const GOOGLE_PROVIDER_REDIRECT_URL = `${HEADLESS_BASE}/auth/provider/redirect`;
