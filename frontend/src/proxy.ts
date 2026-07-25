import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Fast, cookie-presence redirect for logged-out visitors hitting a
 * protected route group — good UX (no flash of protected UI before an API
 * call fails), NOT the actual authorization boundary. A cookie merely being
 * present doesn't prove the session is still valid; every real data fetch
 * is independently authorized by the Django backend (DRF's IsAuthenticated
 * + role/ownership checks), and lib/api-client.ts's 401 handling covers the
 * case where a present-but-expired cookie gets past this check.
 *
 * Role-specific protection (customer vs. staff routes) and the
 * profile-completion gate (customer vs. onboarding) are both client-side,
 * in CustomerAreaGuard/StaffAreaGuard — they need role/profile-completion
 * data from /api/v1/me/, which isn't available to this edge check.
 */
export function proxy(request: NextRequest) {
  const sessionCookie = request.cookies.get("sessionid");
  if (sessionCookie) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/auth/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/onboarding/:path*"],
};
