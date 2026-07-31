/**
 * Client-safe environment access. Only NEXT_PUBLIC_* values are ever read here.
 *
 * Unset (the production default) resolves to "" — relative paths — so
 * requests go through this app's own origin and get proxied to the backend
 * by the rewrites in next.config.ts, keeping Set-Cookie scoped to our
 * domain. Local dev sets this explicitly (see docker-compose.yml) to talk to
 * the backend directly instead.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
