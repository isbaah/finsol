import { ApiError, apiFetch } from "@/lib/api-client";

import type { CustomerProfile, ProfilePayload } from "./types";

export async function getMyProfile(): Promise<CustomerProfile | null> {
  try {
    return await apiFetch<CustomerProfile>("/api/v1/profile/");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export function saveMyProfile(payload: ProfilePayload) {
  return apiFetch<CustomerProfile>("/api/v1/profile/", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
