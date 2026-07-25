import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DashboardMetrics } from "@/features/dashboards/types";

import { MetricCards } from "./metric-cards";

const METRICS: DashboardMetrics = {
  outstanding_portfolio_balance: "1400.00",
  amount_due_this_month: "800.00",
  amount_collected_this_month: "300.00",
  overdue_amount: "500.00",
  active_loans: 2,
  new_request_count: 1,
  pending_approval_count: 0,
  awaiting_disbursement_count: 0,
  pending_payment_claim_count: 0,
};

describe("MetricCards", () => {
  it("shows a skeleton per metric while loading", () => {
    render(<MetricCards metrics={undefined} isLoading isError={false} />);
    expect(screen.getAllByTestId("metric-skeleton")).toHaveLength(5);
  });

  it("renders each metric formatted in GHS", () => {
    render(<MetricCards metrics={METRICS} isLoading={false} isError={false} />);
    expect(screen.getByText("Outstanding portfolio")).toBeInTheDocument();
    expect(screen.getByText("GHS 1,400.00")).toBeInTheDocument();
    expect(screen.getByText("GHS 800.00")).toBeInTheDocument();
    expect(screen.getByText("GHS 300.00")).toBeInTheDocument();
    expect(screen.getByText("GHS 500.00")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows an error message instead of stale numbers on failure", () => {
    render(<MetricCards metrics={undefined} isLoading={false} isError />);
    expect(screen.getByText(/Couldn't load portfolio metrics/)).toBeInTheDocument();
    expect(screen.queryByText("Outstanding portfolio")).not.toBeInTheDocument();
  });
});
