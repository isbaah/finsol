"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { getSession } from "./api";
import type { AllauthEnvelope, SessionState } from "./types";

export const SESSION_QUERY_KEY = ["session"];

function toSessionState(envelope: AllauthEnvelope): SessionState {
  return {
    isAuthenticated: envelope.meta?.is_authenticated ?? false,
    user: envelope.data?.user ?? null,
    pendingFlow: envelope.data?.flows?.find((flow) => flow.is_pending) ?? null,
  };
}

export function useSession() {
  return useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: async () => toSessionState(await getSession()),
    staleTime: 30_000,
  });
}

export function useInvalidateSession() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
}
