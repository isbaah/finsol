"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ADMIN_LOANS_QUERY_KEY } from "@/features/loans/use-loans";

import {
  claimPayment,
  getAdminRepaymentAccount,
  getRepaymentAccount,
  listPayments,
  listPaymentClaims,
  recordPayment,
  resolvePaymentClaim,
  reversePayment,
  updateRepaymentAccount,
} from "./api";
import type { RecordPaymentPayload, RepaymentAccountPayload } from "./types";

export function usePayments(loanId: string) {
  return useQuery({
    queryKey: ["payments", loanId],
    queryFn: () => listPayments(loanId),
    enabled: !!loanId,
  });
}

export function useRecordPayment(loanId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RecordPaymentPayload) => recordPayment(loanId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments", loanId] });
      queryClient.invalidateQueries({ queryKey: [...ADMIN_LOANS_QUERY_KEY, loanId] });
      queryClient.invalidateQueries({ queryKey: ["customer-loan", loanId] });
    },
  });
}

export function useClaimPayment(loanId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ installmentId, note }: { installmentId: string; note: string }) =>
      claimPayment(installmentId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-loan", loanId] });
    },
  });
}

export function usePaymentClaims(status?: "PENDING" | "RESOLVED") {
  return useQuery({
    queryKey: ["payment-claims", status ?? "ALL"],
    queryFn: () => listPaymentClaims(status),
  });
}

export function useResolvePaymentClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: string) => resolvePaymentClaim(claimId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payment-claims"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
    },
  });
}

export function useRepaymentAccount(enabled = true) {
  return useQuery({
    queryKey: ["repayment-account"],
    queryFn: getRepaymentAccount,
    enabled,
  });
}

export function useAdminRepaymentAccount() {
  return useQuery({
    queryKey: ["admin-repayment-account"],
    queryFn: getAdminRepaymentAccount,
  });
}

export function useUpdateRepaymentAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RepaymentAccountPayload) => updateRepaymentAccount(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin-repayment-account"], data);
      queryClient.invalidateQueries({ queryKey: ["repayment-account"] });
    },
  });
}

export function useReversePayment(loanId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paymentId, reason }: { paymentId: string; reason: string }) =>
      reversePayment(paymentId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments", loanId] });
      queryClient.invalidateQueries({ queryKey: [...ADMIN_LOANS_QUERY_KEY, loanId] });
      queryClient.invalidateQueries({ queryKey: ["customer-loan", loanId] });
    },
  });
}
