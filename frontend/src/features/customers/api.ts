import { apiFetch } from "@/lib/api-client";

import type { MaskedCustomerProfile, PaginatedResponse } from "./types";

export function listCustomers() {
  return apiFetch<PaginatedResponse<MaskedCustomerProfile>>("/api/v1/customers/");
}
