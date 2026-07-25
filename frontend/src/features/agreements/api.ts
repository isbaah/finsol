import type { CustomerOffer } from "@/features/offers/types";
import { apiFetch } from "@/lib/api-client";

import type { AcceptOfferPayload, AcceptOfferResult, Agreement } from "./types";

export function acceptOffer(offerId: string, payload: AcceptOfferPayload) {
  return apiFetch<AcceptOfferResult>(`/api/v1/customer/offers/${offerId}/accept/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rejectOffer(offerId: string, reason: string) {
  return apiFetch<CustomerOffer>(`/api/v1/customer/offers/${offerId}/reject/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function requestOfferRevision(offerId: string, reason: string) {
  return apiFetch<CustomerOffer>(`/api/v1/customer/offers/${offerId}/request-revision/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function getAgreement(id: string) {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}/`);
}

export function retryAgreementEmail(id: string) {
  return apiFetch<Agreement>(`/api/v1/admin/agreements/${id}/retry-email/`, { method: "POST" });
}
