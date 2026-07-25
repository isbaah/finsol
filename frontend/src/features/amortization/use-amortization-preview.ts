"use client";

import { useMutation } from "@tanstack/react-query";

import { previewAmortization } from "./api";

// Triggered by an explicit "calculate" action, not fetched automatically —
// a mutation, not a query, even though it reads rather than writes,
// because it's user-initiated on demand and never persists anything
// server-side (Section 24: "Do not persist an offer from the preview endpoint").
export function useAmortizationPreview() {
  return useMutation({
    mutationFn: previewAmortization,
  });
}
