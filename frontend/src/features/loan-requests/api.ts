import { apiFetch } from "@/lib/api-client";

import type {
  AdminLoanRequestDetail,
  AdminLoanRequestListItem,
  AdminLoanRequestListParams,
  LoanRequest,
  LoanRequestCreatePayload,
  PaginatedResponse,
} from "./types";

export function listLoanRequests() {
  return apiFetch<PaginatedResponse<LoanRequest>>("/api/v1/customer/loan-requests/");
}

export function getLoanRequest(id: string) {
  return apiFetch<LoanRequest>(`/api/v1/customer/loan-requests/${id}/`);
}

export function createLoanRequest(payload: LoanRequestCreatePayload) {
  return apiFetch<LoanRequest>("/api/v1/customer/loan-requests/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function cancelLoanRequest(id: string) {
  return apiFetch<LoanRequest>(`/api/v1/customer/loan-requests/${id}/cancel/`, {
    method: "POST",
  });
}

export function listAdminLoanRequests(params: AdminLoanRequestListParams = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.search) query.set("search", params.search);
  if (params.ordering) query.set("ordering", params.ordering);
  const qs = query.toString();
  return apiFetch<PaginatedResponse<AdminLoanRequestListItem>>(
    `/api/v1/admin/loan-requests/${qs ? `?${qs}` : ""}`,
  );
}

export function getAdminLoanRequest(id: string) {
  return apiFetch<AdminLoanRequestDetail>(`/api/v1/admin/loan-requests/${id}/`);
}

export function startReview(id: string) {
  return apiFetch<AdminLoanRequestDetail>(`/api/v1/admin/loan-requests/${id}/start-review/`, {
    method: "POST",
  });
}

export function declineLoanRequest(id: string, reason: string) {
  return apiFetch<AdminLoanRequestDetail>(`/api/v1/admin/loan-requests/${id}/decline/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
