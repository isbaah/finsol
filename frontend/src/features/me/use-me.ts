"use client";

import { useQuery } from "@tanstack/react-query";

import { getMe } from "./api";

export const ME_QUERY_KEY = ["me"];

export function useMe() {
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: getMe,
    staleTime: 30_000,
    // A 401 here means the session has expired — lib/api-client's global
    // handler already reacts to that (toast + redirect), so retrying would
    // only re-fire it three more times for nothing.
    retry: false,
  });
}
