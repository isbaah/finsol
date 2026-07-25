/** Client-safe environment access. Only NEXT_PUBLIC_* values are ever read here. */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
