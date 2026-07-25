"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useMe } from "@/features/me/use-me";

/** Frontend-only convenience: a customer landing in the (admin) route
 * group is sent back to their own dashboard. Real enforcement is the
 * has_any_role(*STAFF_ROLES) permission on every staff API endpoint. */
export function StaffAreaGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: me, isLoading } = useMe();
  const isCustomer = !!me?.is_customer;

  useEffect(() => {
    if (isLoading || !me) return;
    if (isCustomer) {
      router.replace("/dashboard");
    }
  }, [isLoading, me, isCustomer, router]);

  if (isCustomer) return null;

  return <>{children}</>;
}
