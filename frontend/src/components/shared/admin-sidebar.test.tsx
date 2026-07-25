import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminSidebar } from "./admin-sidebar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/loans/some-loan-id",
}));

describe("AdminSidebar", () => {
  it("renders every destination and marks the active section", () => {
    render(<AdminSidebar />);

    // Desktop sidebar + mobile strip both render the same items.
    const loansLinks = screen.getAllByRole("link", { name: "Loans" });
    expect(loansLinks.length).toBeGreaterThan(0);
    for (const link of loansLinks) {
      expect(link).toHaveAttribute("aria-current", "page");
    }

    const dashboardLinks = screen.getAllByRole("link", { name: "Dashboard" });
    for (const link of dashboardLinks) {
      expect(link).not.toHaveAttribute("aria-current");
    }

    for (const label of ["Loan Requests", "Customers", "SMS Activity"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
  });
});
