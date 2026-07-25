"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { cancelLoanRequest, createLoanRequest, getLoanRequest, listLoanRequests } from "./api";

export const LOAN_REQUESTS_QUERY_KEY = ["loan-requests"];

export function useLoanRequests() {
  return useQuery({
    queryKey: LOAN_REQUESTS_QUERY_KEY,
    queryFn: listLoanRequests,
  });
}

export function useLoanRequest(id: string) {
  return useQuery({
    queryKey: [...LOAN_REQUESTS_QUERY_KEY, id],
    queryFn: () => getLoanRequest(id),
  });
}

export function useCreateLoanRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createLoanRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOAN_REQUESTS_QUERY_KEY });
    },
  });
}

export function useCancelLoanRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: cancelLoanRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOAN_REQUESTS_QUERY_KEY });
    },
  });
}
