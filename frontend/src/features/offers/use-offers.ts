"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ADMIN_LOAN_REQUESTS_QUERY_KEY } from "@/features/loan-requests/use-admin-loan-requests";

import { createOffer, getAdminOffer, updateDraftOffer } from "./api";
import type { OfferWritePayload } from "./types";

export const ADMIN_OFFER_QUERY_KEY = ["admin-offer"];

export function useAdminOffer(id: string) {
  return useQuery({
    queryKey: [...ADMIN_OFFER_QUERY_KEY, id],
    queryFn: () => getAdminOffer(id),
    enabled: !!id,
  });
}

export function useCreateOffer(loanRequestId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OfferWritePayload) => createOffer(loanRequestId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_LOAN_REQUESTS_QUERY_KEY });
    },
  });
}

export function useUpdateDraftOffer(offerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OfferWritePayload) => updateDraftOffer(offerId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...ADMIN_OFFER_QUERY_KEY, offerId] });
      queryClient.invalidateQueries({ queryKey: ADMIN_LOAN_REQUESTS_QUERY_KEY });
    },
  });
}
