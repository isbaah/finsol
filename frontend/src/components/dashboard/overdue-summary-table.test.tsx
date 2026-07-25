import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getOverdueSummary } from "@/features/dashboards/api";
import type { OverdueSummary } from "@/features/dashboards/types";

import { OverdueSummaryTable } from "./overdue-summary-table";

vi.mock("@/features/dashboards/api", () => ({
  getOverdueSummary: vi.fn(),
}));

const SUMMARY: OverdueSummary = {
  buckets: [
    {
      label: "1-7 days",
      min_days: 1,
      max_days: 7,
      installment_count: 2,
      loan_count: 2,
      outstanding_total: "300.00",
    },
    {
      label: "8-30 days",
      min_days: 8,
      max_days: 30,
      installment_count: 0,
      loan_count: 0,
      outstanding_total: "0.00",
    },
    {
      label: "31-60 days",
      min_days: 31,
      max_days: 60,
      installment_count: 1,
      loan_count: 1,
      outstanding_total: "400.00",
    },
    {
      label: "61+ days",
      min_days: 61,
      max_days: null,
      installment_count: 0,
      loan_count: 0,
      outstanding_total: "0.00",
    },
  ],
  total_outstanding: "700.00",
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("OverdueSummaryTable", () => {
  it("celebrates an empty overdue book", async () => {
    vi.mocked(getOverdueSummary).mockResolvedValue({
      buckets: SUMMARY.buckets.map((bucket) => ({
        ...bucket,
        installment_count: 0,
        loan_count: 0,
        outstanding_total: "0.00",
      })),
      total_outstanding: "0.00",
    });
    renderWithProviders(<OverdueSummaryTable />);

    expect(await screen.findByText("Nothing is overdue. Well done.")).toBeInTheDocument();
  });

  it("renders every age bucket and the total", async () => {
    vi.mocked(getOverdueSummary).mockResolvedValue(SUMMARY);
    renderWithProviders(<OverdueSummaryTable />);

    expect(await screen.findByText("1-7 days")).toBeInTheDocument();
    expect(screen.getByText("61+ days")).toBeInTheDocument();
    expect(screen.getByText("GHS 400.00")).toBeInTheDocument();
    expect(screen.getByText("GHS 700.00")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View overdue loans" })).toHaveAttribute(
      "href",
      "/admin/loans?status=OVERDUE",
    );
  });
});
