import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { reversePayment } from "@/features/repayments/api";
import type { Payment } from "@/features/repayments/types";

import { PaymentHistoryTable } from "./payment-history-table";

vi.mock("@/features/repayments/api", () => ({
  reversePayment: vi.fn(),
}));

const POSTED_PAYMENT: Payment = {
  id: "payment-1",
  receipt_number: "RCT-2026-000001",
  amount: "300.00",
  payment_date: "2026-07-20",
  payment_method: "CASH",
  status: "POSTED",
  created_at: "2026-07-20T00:00:00Z",
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("PaymentHistoryTable", () => {
  beforeEach(() => {
    vi.mocked(reversePayment).mockReset();
  });

  it("shows an empty state when there are no payments", () => {
    renderWithProviders(<PaymentHistoryTable loanId="loan-1" payments={[]} showActions />);
    expect(screen.getByText("No payments recorded yet.")).toBeInTheDocument();
  });

  it("does not show a reverse action on the customer's read-only view", () => {
    renderWithProviders(
      <PaymentHistoryTable loanId="loan-1" payments={[POSTED_PAYMENT]} showActions={false} />,
    );
    expect(screen.queryByRole("button", { name: "Reverse" })).not.toBeInTheDocument();
  });

  it("reverses a posted payment after a reason is supplied", async () => {
    vi.mocked(reversePayment).mockResolvedValue({ ...POSTED_PAYMENT, status: "REVERSED" });
    const user = userEvent.setup();
    renderWithProviders(
      <PaymentHistoryTable loanId="loan-1" payments={[POSTED_PAYMENT]} showActions />,
    );

    await user.click(screen.getByRole("button", { name: "Reverse" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Reason"), "Recorded against the wrong loan");
    await user.click(within(dialog).getByRole("button", { name: "Confirm reversal" }));

    await waitFor(() => expect(reversePayment).toHaveBeenCalledTimes(1));
    expect(reversePayment).toHaveBeenCalledWith("payment-1", "Recorded against the wrong loan");
  });

  it("requires a reason before submitting a reversal", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <PaymentHistoryTable loanId="loan-1" payments={[POSTED_PAYMENT]} showActions />,
    );

    await user.click(screen.getByRole("button", { name: "Reverse" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Confirm reversal" }));

    expect(
      await within(dialog).findByText("A reason is required to reverse a payment."),
    ).toBeInTheDocument();
    expect(reversePayment).not.toHaveBeenCalled();
  });
});
