import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import type { AllauthFieldError } from "./types";

/** Maps allauth's {message, code, param} error list onto react-hook-form
 * field errors, falling back to a named field (usually the password field,
 * or a form-level field) for errors with no `param` (e.g. "wrong
 * credentials" isn't tied to one specific input). */
export function applyAllauthErrors<T extends FieldValues>(
  errors: AllauthFieldError[] | undefined,
  setError: UseFormSetError<T>,
  fallbackField: Path<T>,
): void {
  if (!errors || errors.length === 0) return;
  for (const err of errors) {
    const field = (err.param as Path<T> | undefined) ?? fallbackField;
    setError(field, { type: "server", message: err.message });
  }
}
