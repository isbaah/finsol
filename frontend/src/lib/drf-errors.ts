import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import type { ApiError } from "./api-client";

/** Maps a DRF ValidationError body — `{"field_name": ["message", ...]}`,
 * plus an optional `non_field_errors` key — onto react-hook-form field
 * errors. Distinct from features/auth/errors.ts's applyAllauthErrors: our
 * own /api/v1/... endpoints use DRF's error shape, not allauth headless's
 * {message, code, param} envelope. */
export function applyDrfErrors<T extends FieldValues>(
  error: ApiError,
  setError: UseFormSetError<T>,
  fallbackField: Path<T>,
): void {
  const body = error.body;
  if (!body || typeof body !== "object") return;

  for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
    const message = Array.isArray(value) ? String(value[0]) : String(value);
    const field = (key === "non_field_errors" ? fallbackField : key) as Path<T>;
    setError(field, { type: "server", message });
  }
}
