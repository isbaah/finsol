import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CustomerLoan } from "@/features/loans/types";

import { CustomerLoanSummary } from "./customer-loan-summary";

vi.mock("@/features/agreements/use-agreements", () => ({
  useAgreement: () => ({
    data: {
      id: "agreement-1",
      typed_legal_name: "Ama Owusu",
      accepted_at: "2026-06-01T00:00:00Z",
      download_url: "/api/v1/customer/agreements/agreement-1/download/",
    },
  }),
}));

const LOAN: CustomerLoan = {
  id: "loan-1",
  loan_number: "LN-2026-000001",
  request_number: "REQ-2026-000001",
  status: "ACTIVE",
  principal: "1000.00",
  total_interest: "200.00",
  total_repayable: "1200.00",
  amount_disbursed: "1000.00",
  amount_repaid: "300.00",
  outstanding_balance: "900.00",
  approved_at: "2026-06-01T00:00:00Z",
  disbursed_at: "2026-06-02T00:00:00Z",
  agreement_id: "agreement-1",
  installments: [
    {
      id: "inst-1",
      sequence_number: 1,
      due_date: "2026-07-01",
      principal_due: "250.00",
      interest_due: "50.00",
      total_due: "300.00",
      amount_paid: "300.00",
      outstanding_amount: "0.00",
      status: "PAID",
    },
    {
      id: "inst-2",
      sequence_number: 2,
      due_date: "2026-08-01",
      principal_due: "250.00",
      interest_due: "50.00",
      total_due: "300.00",
      amount_paid: "0.00",
      outstanding_amount: "300.00",
      status: "UPCOMING",
    },
  ],
  payments: [
    {
      id: "payment-1",
      receipt_number: "RCT-2026-000001",
      amount: "300.00",
      payment_date: "2026-06-28",
      payment_method: "MOBILE_MONEY",
      status: "POSTED",
      created_at: "2026-06-28T00:00:00Z",
    },
  ],
  created_at: "2026-06-01T00:00:00Z",
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("CustomerLoanSummary", () => {
  it("summarises repaid, outstanding, and the next unpaid installment", () => {
    renderWithProviders(<CustomerLoanSummary loan={LOAN} />);

    expect(screen.getByText("Your loan — LN-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("GHS 1,000.00")).toBeInTheDocument();
    expect(screen.getByText("GHS 900.00")).toBeInTheDocument();
    // Next payment comes from the first non-settled installment (#2), not
    // the already-paid first one.
    expect(screen.getByText("due 1 Aug 2026")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("lists recent posted payments and links to the agreement PDF", () => {
    renderWithProviders(<CustomerLoanSummary loan={LOAN} />);

    expect(screen.getByText(/RCT-2026-000001/)).toBeInTheDocument();
    // Button's `render` prop stamps role="button" on the anchors.
    expect(screen.getByRole("button", { name: "Download agreement (PDF)" })).toHaveAttribute(
      "href",
      "/api/v1/customer/agreements/agreement-1/download/",
    );
    expect(screen.getByRole("button", { name: "View full loan" })).toHaveAttribute(
      "href",
      "/loans/loan-1",
    );
  });
});
