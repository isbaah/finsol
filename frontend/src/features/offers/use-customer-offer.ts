"use client";

import { useQuery } from "@tanstack/react-query";

import { getCustomerOffer } from "./api";

export function useCustomerOffer(id: string) {
  return useQuery({
    queryKey: ["customer-offer", id],
    queryFn: () => getCustomerOffer(id),
    enabled: !!id,
  });
}
