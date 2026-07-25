import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "./proxy";

describe("proxy", () => {
  it("redirects to /auth/login when no session cookie is present", () => {
    const request = new NextRequest("http://localhost:3000/dashboard");

    const response = proxy(request);

    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location")!);
    expect(location.pathname).toBe("/auth/login");
    expect(location.searchParams.get("next")).toBe("/dashboard");
  });

  it("preserves the originally requested admin path in the redirect", () => {
    const request = new NextRequest("http://localhost:3000/admin/dashboard");

    const response = proxy(request);

    const location = new URL(response.headers.get("location")!);
    expect(location.searchParams.get("next")).toBe("/admin/dashboard");
  });

  it("allows the request through when a session cookie is present", () => {
    const request = new NextRequest("http://localhost:3000/dashboard", {
      headers: { cookie: "sessionid=some-session-value" },
    });

    const response = proxy(request);

    expect(response.headers.get("location")).toBeNull();
  });
});
