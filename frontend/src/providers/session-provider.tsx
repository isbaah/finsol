"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { setUnauthorizedHandler } from "@/lib/api-client";
import { SESSION_QUERY_KEY } from "@/features/auth/use-session";

/**
 * Registers a global handler for 401 responses from our own /api/v1/...
 * endpoints (see lib/api-client.ts). A 401 there — as opposed to from
 * allauth's own endpoints, which use 401 as normal flow-control — means a
 * session that this UI believed was valid just stopped being valid
 * (expired, revoked elsewhere, etc.), so it's treated as a one-shot event:
 * tell the user, drop the cached session, send them to sign in again.
 */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      toast.error("Your session has expired. Please sign in again.");
      queryClient.setQueryData(SESSION_QUERY_KEY, {
        isAuthenticated: false,
        user: null,
        pendingFlow: null,
      });
      router.push("/auth/login");
    });
    return () => setUnauthorizedHandler(null);
  }, [router, queryClient]);

  return children;
}
