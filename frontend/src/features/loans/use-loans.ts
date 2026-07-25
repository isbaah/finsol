"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveLoan,
  disburseLoan,
  getAdminLoan,
  getCustomerLoan,
  getPayoutDetails,
  listAdminLoans,
  listCustomerLoans,
} from "./api";
import type { AdminLoanListParams, DisbursementPayload } from "./types";

export const ADMIN_LOANS_QUERY_KEY = ["admin-loans"];

export function useCustomerLoans() {
  return useQuery({ queryKey: ["customer-loans"], queryFn: listCustomerLoans });
}

export function useCustomerLoan(id: string) {
  return useQuery({
    queryKey: ["customer-loan", id],
    queryFn: () => getCustomerLoan(id),
    enabled: !!id,
  });
}

export function useAdminLoans(params: AdminLoanListParams) {
  return useQuery({
    queryKey: [...ADMIN_LOANS_QUERY_KEY, params],
    queryFn: () => listAdminLoans(params),
  });
}

export function useAdminLoan(id: string) {
  return useQuery({
    queryKey: [...ADMIN_LOANS_QUERY_KEY, id],
    queryFn: () => getAdminLoan(id),
    enabled: !!id,
  });
}

export function useApproveLoan(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => approveLoan(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_LOANS_QUERY_KEY });
    },
  });
}

export function useDisburseLoan(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DisbursementPayload) => disburseLoan(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_LOANS_QUERY_KEY });
    },
  });
}

export function usePayoutDetails(loanId: string) {
  return useQuery({
    queryKey: ["payout-details", loanId],
    queryFn: () => getPayoutDetails(loanId),
    enabled: false, // only fetched on an explicit "Reveal" click, never eagerly
  });
}
