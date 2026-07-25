"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { declineLoanRequest, getAdminLoanRequest, listAdminLoanRequests, startReview } from "./api";
import type { AdminLoanRequestListParams } from "./types";

export const ADMIN_LOAN_REQUESTS_QUERY_KEY = ["admin-loan-requests"];

export function useAdminLoanRequests(params: AdminLoanRequestListParams) {
  return useQuery({
    queryKey: [...ADMIN_LOAN_REQUESTS_QUERY_KEY, params],
    queryFn: () => listAdminLoanRequests(params),
  });
}

export function useAdminLoanRequest(id: string) {
  return useQuery({
    queryKey: [...ADMIN_LOAN_REQUESTS_QUERY_KEY, id],
    queryFn: () => getAdminLoanRequest(id),
  });
}

export function useStartReview(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => startReview(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_LOAN_REQUESTS_QUERY_KEY });
    },
  });
}

export function useDeclineLoanRequest(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => declineLoanRequest(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_LOAN_REQUESTS_QUERY_KEY });
    },
  });
}
