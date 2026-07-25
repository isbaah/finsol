"use client";

import { useQuery } from "@tanstack/react-query";

import { listCustomers } from "./api";

export function useCustomers() {
  return useQuery({
    queryKey: ["customers"],
    queryFn: listCustomers,
  });
}
