"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useSession } from "@/features/auth/use-session";

/**
 * Django redirects here after a successful Google OAuth round-trip (a
 * failure redirects straight to /auth/login?error=social instead — see
 * HEADLESS_FRONTEND_URLS['socialaccount_login_error'] in
 * backend/config/settings/base.py). The session cookie is already set by
 * the time the browser lands here; this page just confirms it and routes
 * onward.
 */
export default function GoogleCallbackPage() {
  const router = useRouter();
  const { data, isLoading } = useSession();

  useEffect(() => {
    if (isLoading) return;
    router.replace(data?.isAuthenticated ? "/dashboard" : "/auth/login?error=social");
  }, [isLoading, data, router]);

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
      <p className="text-muted-foreground text-sm">Finishing sign-in…</p>
    </main>
  );
}
