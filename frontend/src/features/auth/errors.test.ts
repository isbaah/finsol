import { describe, expect, it, vi } from "vitest";

import { applyAllauthErrors } from "./errors";

describe("applyAllauthErrors", () => {
  it("does nothing when there are no errors", () => {
    const setError = vi.fn();

    applyAllauthErrors(undefined, setError, "email");

    expect(setError).not.toHaveBeenCalled();
  });

  it("maps a field-specific error to its param", () => {
    const setError = vi.fn();

    applyAllauthErrors(
      [{ message: "This field is required.", code: "required", param: "email" }],
      setError,
      "email",
    );

    expect(setError).toHaveBeenCalledWith("email", {
      type: "server",
      message: "This field is required.",
    });
  });

  it("falls back to the given field when the error has no param", () => {
    const setError = vi.fn();

    applyAllauthErrors(
      [{ message: "Incorrect email or password.", code: "invalid_login" }],
      setError,
      "password",
    );

    expect(setError).toHaveBeenCalledWith("password", {
      type: "server",
      message: "Incorrect email or password.",
    });
  });

  it("applies every error in the list", () => {
    const setError = vi.fn();

    applyAllauthErrors(
      [
        { message: "Too short.", code: "min_length", param: "password" },
        { message: "Already taken.", code: "email_taken", param: "email" },
      ],
      setError,
      "email",
    );

    expect(setError).toHaveBeenCalledTimes(2);
  });
});
