import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("renders the app name and a sign-in link", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: /loan management system/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toHaveAttribute("href", "/login");
  });
});
