import { apiFetch } from "@/lib/api-client";

import type { AmortizationPreviewRequest, AmortizationPreviewResponse } from "./types";

export function previewAmortization(payload: AmortizationPreviewRequest) {
  return apiFetch<AmortizationPreviewResponse>("/api/v1/admin/offers/preview/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
