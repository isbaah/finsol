import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("renders the hero with sign-up and sign-in actions", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: /borrowing, without the back and forth/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /get started/i })).toHaveAttribute(
      "href",
      "/auth/signup",
    );
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute("href", "/auth/login");
  });
});
