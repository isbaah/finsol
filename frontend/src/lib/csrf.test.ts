import { afterEach, describe, expect, it } from "vitest";

import { getCsrfToken } from "./csrf";

describe("getCsrfToken", () => {
  afterEach(() => {
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  });

  it("returns null when the cookie is absent", () => {
    expect(getCsrfToken()).toBeNull();
  });

  it("reads and decodes the csrftoken cookie", () => {
    document.cookie = "csrftoken=abc123";

    expect(getCsrfToken()).toBe("abc123");
  });

  it("does not match cookies that merely contain csrftoken as a substring", () => {
    document.cookie = "othercsrftoken=wrong";

    expect(getCsrfToken()).toBeNull();
  });
});
