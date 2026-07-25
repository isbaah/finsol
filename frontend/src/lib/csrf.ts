/**
 * Reads the `csrftoken` cookie Django's CSRF middleware sets. The cookie
 * value itself is the token to echo back — as the `X-CSRFToken` header for
 * fetch calls, or as the `csrfmiddlewaretoken` form field for a plain HTML
 * form submission (see GoogleSignInButton). CSRF_COOKIE_HTTPONLY is left at
 * Django's default (false) specifically so this works.
 */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}
