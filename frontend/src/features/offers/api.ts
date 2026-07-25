import { apiFetch } from "@/lib/api-client";

import type { AdminOfferDetail, CustomerOffer, OfferWritePayload } from "./types";

export function createOffer(loanRequestId: string, payload: OfferWritePayload) {
  return apiFetch<AdminOfferDetail>(`/api/v1/admin/loan-requests/${loanRequestId}/offers/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAdminOffer(id: string) {
  return apiFetch<AdminOfferDetail>(`/api/v1/admin/offers/${id}/`);
}

export function updateDraftOffer(id: string, payload: OfferWritePayload) {
  return apiFetch<AdminOfferDetail>(`/api/v1/admin/offers/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function sendOffer(id: string) {
  return apiFetch<AdminOfferDetail>(`/api/v1/admin/offers/${id}/send/`, {
    method: "POST",
  });
}

export function getCustomerOffer(id: string) {
  return apiFetch<CustomerOffer>(`/api/v1/customer/offers/${id}/`);
}
