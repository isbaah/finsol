import { apiFetch } from "@/lib/api-client";
import type { PaginatedResponse } from "@/features/loan-requests/types";

import type {
  AdminLoanDetail,
  AdminLoanListItem,
  AdminLoanListParams,
  CustomerLoan,
  DisbursementPayload,
  PayoutDetails,
} from "./types";

export function getCustomerLoan(id: string) {
  return apiFetch<CustomerLoan>(`/api/v1/customer/loans/${id}/`);
}

export function listCustomerLoans() {
  return apiFetch<PaginatedResponse<CustomerLoan>>("/api/v1/customer/loans/");
}

export function listAdminLoans(params: AdminLoanListParams = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.search) query.set("search", params.search);
  if (params.ordering) query.set("ordering", params.ordering);
  const qs = query.toString();
  return apiFetch<PaginatedResponse<AdminLoanListItem>>(
    `/api/v1/admin/loans/${qs ? `?${qs}` : ""}`,
  );
}

export function getAdminLoan(id: string) {
  return apiFetch<AdminLoanDetail>(`/api/v1/admin/loans/${id}/`);
}

export function approveLoan(id: string) {
  return apiFetch<AdminLoanDetail>(`/api/v1/admin/loans/${id}/approve/`, { method: "POST" });
}

export function disburseLoan(id: string, payload: DisbursementPayload) {
  if (payload.evidence_file) {
    const formData = new FormData();
    formData.set("amount", payload.amount);
    formData.set("method", payload.method);
    if (payload.external_transaction_reference) {
      formData.set("external_transaction_reference", payload.external_transaction_reference);
    }
    if (payload.notes) formData.set("notes", payload.notes);
    formData.set("evidence_file", payload.evidence_file);
    return apiFetch<AdminLoanDetail>(`/api/v1/admin/loans/${id}/disburse/`, {
      method: "POST",
      body: formData,
    });
  }
  return apiFetch<AdminLoanDetail>(`/api/v1/admin/loans/${id}/disburse/`, {
    method: "POST",
    body: JSON.stringify({
      amount: payload.amount,
      method: payload.method,
      external_transaction_reference: payload.external_transaction_reference ?? "",
      notes: payload.notes ?? "",
    }),
  });
}

export function getPayoutDetails(loanId: string) {
  return apiFetch<PayoutDetails>(`/api/v1/admin/loans/${loanId}/payout-details/`);
}
