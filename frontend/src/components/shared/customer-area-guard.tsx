"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useMe } from "@/features/me/use-me";

const ONBOARDING_PATH = "/onboarding/profile";

/**
 * Frontend-only routing convenience for the (customer) route group — real
 * enforcement is server-side (Section 26: "Never rely on hiding a frontend
 * button as authorisation"). Two jobs:
 *  1. send staff away to the admin area, since CustomerProfile/onboarding
 *     is a customer-only concept;
 *  2. send a customer with no completed profile to /onboarding/profile
 *     before they can see any other customer page.
 */
export function CustomerAreaGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: me, isLoading } = useMe();

  const needsOnboarding =
    !!me?.is_customer && !me.profile_completed && pathname !== ONBOARDING_PATH;
  const isStaff = !!me && !me.is_customer;

  useEffect(() => {
    if (isLoading || !me) return;
    if (isStaff) {
      router.replace("/admin/dashboard");
    } else if (needsOnboarding) {
      router.replace(ONBOARDING_PATH);
    }
  }, [isLoading, me, isStaff, needsOnboarding, router]);

  if (isStaff || needsOnboarding) return null;

  return <>{children}</>;
}
