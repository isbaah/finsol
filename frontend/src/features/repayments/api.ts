import { apiFetch } from "@/lib/api-client";
import type { PaginatedResponse } from "@/features/loan-requests/types";

import type {
  Payment,
  PaymentClaim,
  RecordPaymentPayload,
  RepaymentAccount,
  RepaymentAccountPayload,
} from "./types";

export function listPayments(loanId: string) {
  return apiFetch<PaginatedResponse<Payment>>(`/api/v1/admin/loans/${loanId}/repayments/`);
}

export function recordPayment(loanId: string, payload: RecordPaymentPayload) {
  if (payload.evidence_file) {
    const formData = new FormData();
    formData.set("amount", payload.amount);
    formData.set("payment_date", payload.payment_date);
    formData.set("payment_method", payload.payment_method);
    if (payload.external_transaction_reference) {
      formData.set("external_transaction_reference", payload.external_transaction_reference);
    }
    if (payload.notes) formData.set("notes", payload.notes);
    if (payload.idempotency_key) formData.set("idempotency_key", payload.idempotency_key);
    formData.set("evidence_file", payload.evidence_file);
    return apiFetch<Payment>(`/api/v1/admin/loans/${loanId}/repayments/`, {
      method: "POST",
      body: formData,
    });
  }
  return apiFetch<Payment>(`/api/v1/admin/loans/${loanId}/repayments/`, {
    method: "POST",
    body: JSON.stringify({
      amount: payload.amount,
      payment_date: payload.payment_date,
      payment_method: payload.payment_method,
      external_transaction_reference: payload.external_transaction_reference ?? "",
      notes: payload.notes ?? "",
      idempotency_key: payload.idempotency_key ?? "",
    }),
  });
}

export function reversePayment(paymentId: string, reason: string) {
  return apiFetch<Payment>(`/api/v1/admin/repayments/${paymentId}/reverse/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function claimPayment(installmentId: string, note: string) {
  return apiFetch<PaymentClaim>(`/api/v1/customer/installments/${installmentId}/claim-payment/`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export function listPaymentClaims(status?: "PENDING" | "RESOLVED") {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<PaginatedResponse<PaymentClaim>>(`/api/v1/admin/payment-claims/${qs}`);
}

export function resolvePaymentClaim(claimId: string) {
  return apiFetch<PaymentClaim>(`/api/v1/admin/payment-claims/${claimId}/resolve/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getRepaymentAccount() {
  return apiFetch<RepaymentAccount>("/api/v1/repayment-account/");
}

export function getAdminRepaymentAccount() {
  return apiFetch<RepaymentAccount>("/api/v1/admin/repayment-account/");
}

export function updateRepaymentAccount(payload: RepaymentAccountPayload) {
  return apiFetch<RepaymentAccount>("/api/v1/admin/repayment-account/", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
