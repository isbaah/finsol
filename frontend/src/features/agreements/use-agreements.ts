"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  acceptOffer,
  getAgreement,
  rejectOffer,
  requestOfferRevision,
  retryAgreementEmail,
} from "./api";
import type { AcceptOfferPayload } from "./types";

export function useAgreement(id: string) {
  return useQuery({
    queryKey: ["agreement", id],
    queryFn: () => getAgreement(id),
    enabled: !!id,
  });
}

export function useAcceptOffer(offerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AcceptOfferPayload) => acceptOffer(offerId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-offer", offerId] });
    },
  });
}

export function useRejectOffer(offerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => rejectOffer(offerId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-offer", offerId] });
    },
  });
}

export function useRequestOfferRevision(offerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => requestOfferRevision(offerId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customer-offer", offerId] });
    },
  });
}

export function useRetryAgreementEmail(agreementId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => retryAgreementEmail(agreementId),
    onSuccess: (data) => {
      queryClient.setQueryData(["agreement", agreementId], data);
    },
  });
}
