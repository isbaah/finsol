"use client";

import { useEffect, useState } from "react";

import { GOOGLE_PROVIDER_REDIRECT_URL } from "@/features/auth/api";
import { getCsrfToken } from "@/lib/csrf";

/**
 * This is a real HTML form submit (full page navigation), not a fetch()
 * call. RedirectToProviderView expects a form-encoded POST and responds
 * with an HTTP redirect the browser must follow through to
 * accounts.google.com — something fetch() can't drive. The CSRF token
 * therefore has to travel as the `csrfmiddlewaretoken` form field, not an
 * X-CSRFToken header.
 *
 * The token is read post-mount (not during the initial render) so server
 * and client agree on the first paint — document.cookie is only available
 * client-side, and the cookie itself is only set once the session-discovery
 * call in SessionProvider has run at least once.
 */
export function GoogleSignInButton() {
  const [csrfToken, setCsrfToken] = useState("");
  const [callbackUrl, setCallbackUrl] = useState("/auth/google/callback");

  useEffect(() => {
    // Synchronizing with two external, browser-only sources (the CSRF
    // cookie, the real origin) that don't exist during SSR — not state
    // that could be computed during render without a hydration mismatch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCsrfToken(getCsrfToken() ?? "");
    setCallbackUrl(`${window.location.origin}/auth/google/callback`);
  }, []);

  return (
    <form action={GOOGLE_PROVIDER_REDIRECT_URL} method="POST" className="w-full max-w-sm">
      <input type="hidden" name="provider" value="google" />
      <input type="hidden" name="process" value="login" />
      <input type="hidden" name="callback_url" value={callbackUrl} />
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
      <button
        type="submit"
        disabled={!csrfToken}
        className="border-input bg-background text-foreground hover:bg-muted inline-flex h-8 w-full items-center justify-center gap-2 rounded-lg border px-2.5 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50"
      >
        Continue with Google
      </button>
    </form>
  );
}
