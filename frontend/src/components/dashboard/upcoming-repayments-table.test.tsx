import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getUpcomingRepayments } from "@/features/dashboards/api";
import type { UpcomingRepaymentRow } from "@/features/dashboards/types";

import { UpcomingRepaymentsTable } from "./upcoming-repayments-table";

vi.mock("@/features/dashboards/api", () => ({
  getUpcomingRepayments: vi.fn(),
}));

const ROW: UpcomingRepaymentRow = {
  installment_id: "inst-1",
  loan_id: "loan-1",
  loan_number: "LN-2026-000001",
  customer_name: "Ama Owusu",
  sequence_number: 2,
  total_due: "300.00",
  outstanding_amount: "150.00",
  due_date: "2026-07-27",
  days_remaining: 3,
  status: "PARTIALLY_PAID",
  last_sms_status: "SENT",
  last_sms_type: "REPAYMENT_DUE_3_DAYS",
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("UpcomingRepaymentsTable", () => {
  it("shows an empty state when nothing is due within seven days", async () => {
    vi.mocked(getUpcomingRepayments).mockResolvedValue([]);
    renderWithProviders(<UpcomingRepaymentsTable />);

    expect(
      await screen.findByText("No installments fall due in the next seven days."),
    ).toBeInTheDocument();
  });

  it("renders a row with amounts, days remaining, SMS status, and actions", async () => {
    vi.mocked(getUpcomingRepayments).mockResolvedValue([ROW]);
    renderWithProviders(<UpcomingRepaymentsTable />);

    expect(await screen.findByText("Ama Owusu")).toBeInTheDocument();
    expect(screen.getByText("GHS 300.00")).toBeInTheDocument();
    expect(screen.getByText("GHS 150.00")).toBeInTheDocument();
    expect(screen.getByText("3 days")).toBeInTheDocument();
    expect(screen.getByText("SENT")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View loan" })).toHaveAttribute(
      "href",
      "/admin/loans/loan-1",
    );
    expect(screen.getByRole("link", { name: "SMS history" })).toHaveAttribute(
      "href",
      "/admin/sms-activity?loan=loan-1",
    );
    expect(screen.getByRole("button", { name: "Send reminder" })).toBeInTheDocument();
  });
});
