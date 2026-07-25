import { apiFetch } from "@/lib/api-client";

import type { Me } from "./types";

export function getMe() {
  return apiFetch<Me>("/api/v1/me/");
}
