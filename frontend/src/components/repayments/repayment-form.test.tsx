import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { recordPayment } from "@/features/repayments/api";
import type { AdminLoanDetail } from "@/features/loans/types";
import { ApiError } from "@/lib/api-client";

import { RepaymentForm } from "./repayment-form";

vi.mock("@/features/repayments/api", () => ({
  recordPayment: vi.fn(),
}));

const LOAN: AdminLoanDetail = {
  id: "loan-1",
  loan_number: "LN-2026-000001",
  request_number: "REQ-2026-000001",
  customer_email: "customer@example.com",
  customer_name: "Ama Owusu",
  customer_phone: "+233241234567",
  status: "ACTIVE",
  principal: "1000.00",
  total_interest: "0.00",
  total_repayable: "1000.00",
  amount_disbursed: "1000.00",
  amount_repaid: "0.00",
  outstanding_balance: "1000.00",
  approved_by_name: "Kwame Boateng",
  approved_at: "2026-07-01T00:00:00Z",
  disbursed_at: "2026-07-02T00:00:00Z",
  closed_at: null,
  agreement_id: "agreement-1",
  disbursement: null,
  installments: [
    {
      id: "inst-1",
      sequence_number: 1,
      due_date: "2027-01-01",
      principal_due: "1000.00",
      interest_due: "0.00",
      total_due: "1000.00",
      amount_paid: "0.00",
      outstanding_amount: "1000.00",
      status: "UPCOMING",
    },
  ],
  payments: [],
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("RepaymentForm", () => {
  beforeEach(() => {
    vi.mocked(recordPayment).mockReset();
  });

  it("opens the modal, prefills the next installment amount, and records a payment", async () => {
    vi.mocked(recordPayment).mockResolvedValue({
      id: "payment-1",
      receipt_number: "RCT-2026-000001",
      amount: "1000.00",
      payment_date: "2026-07-20",
      payment_method: "CASH",
      status: "POSTED",
      created_at: "2026-07-20T00:00:00Z",
    });
    const user = userEvent.setup();
    renderWithProviders(<RepaymentForm loan={LOAN} />);

    await user.click(screen.getByRole("button", { name: "Record repayment" }));

    const dialog = await screen.findByRole("dialog");
    const amountInput = within(dialog).getByLabelText("Amount received (GHS)");
    expect(amountInput).toHaveValue("1000.00");

    await user.click(within(dialog).getByRole("button", { name: "Record repayment" }));

    await waitFor(() => expect(recordPayment).toHaveBeenCalledTimes(1));
    expect(recordPayment).toHaveBeenCalledWith(
      "loan-1",
      expect.objectContaining({ amount: "1000.00", payment_method: "MOBILE_MONEY" }),
    );
  });

  it("shows the server's conflict detail on a 409 instead of a generic error", async () => {
    vi.mocked(recordPayment).mockRejectedValue(
      new ApiError(409, { detail: "Payment amount exceeds the loan's outstanding balance." }),
    );
    const user = userEvent.setup();
    renderWithProviders(<RepaymentForm loan={LOAN} />);

    await user.click(screen.getByRole("button", { name: "Record repayment" }));
    const dialog = await screen.findByRole("dialog");
    within(dialog).getByLabelText("Amount received (GHS)");
    await user.click(within(dialog).getByRole("button", { name: "Record repayment" }));

    expect(
      await within(dialog).findByText("Payment amount exceeds the loan's outstanding balance."),
    ).toBeInTheDocument();
  });
});
