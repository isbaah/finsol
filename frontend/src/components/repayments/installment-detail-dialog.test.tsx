import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { claimPayment } from "@/features/repayments/api";
import type { RepaymentInstallmentSummary } from "@/features/loans/types";
import { ApiError } from "@/lib/api-client";

import { InstallmentDetailDialog } from "./installment-detail-dialog";

vi.mock("@/features/repayments/api", () => ({
  claimPayment: vi.fn(),
  getRepaymentAccount: vi.fn().mockResolvedValue({
    mobile_money_network: "MTN",
    mobile_money_number: "0551234567",
    mobile_money_account_name: "Finsol Ltd",
    bank_name: "",
    bank_account_name: "",
    bank_account_number: "",
    payment_instructions: "Use your loan number as the reference.",
    updated_at: "2026-07-24T00:00:00Z",
  }),
}));

const INSTALLMENT: RepaymentInstallmentSummary = {
  id: "inst-1",
  sequence_number: 2,
  due_date: "2026-08-01",
  principal_due: "250.00",
  interest_due: "50.00",
  total_due: "300.00",
  amount_paid: "100.00",
  outstanding_amount: "200.00",
  status: "PARTIALLY_PAID",
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("InstallmentDetailDialog", () => {
  beforeEach(() => {
    vi.mocked(claimPayment).mockReset();
  });

  it("shows the installment's payment details", async () => {
    renderWithProviders(
      <InstallmentDetailDialog
        loanId="loan-1"
        installment={INSTALLMENT}
        open
        onOpenChange={() => {}}
      />,
    );

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Installment #2")).toBeInTheDocument();
    expect(within(dialog).getByText("GHS 300.00")).toBeInTheDocument();
    expect(within(dialog).getByText("GHS 200.00")).toBeInTheDocument();
    expect(within(dialog).getByText("GHS 100.00")).toBeInTheDocument();
  });

  it("shows the company pay-to account with a copy action", async () => {
    renderWithProviders(
      <InstallmentDetailDialog
        loanId="loan-1"
        installment={INSTALLMENT}
        open
        onOpenChange={() => {}}
      />,
    );

    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("0551234567")).toBeInTheDocument();
    expect(within(dialog).getByText(/MTN — Finsol Ltd/)).toBeInTheDocument();
    expect(
      within(dialog).getByRole("button", { name: /copy mobile money number/i }),
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/use your loan number as the reference/i)).toBeInTheDocument();
  });

  it("sends an I've-paid claim with the note and confirms", async () => {
    vi.mocked(claimPayment).mockResolvedValue({
      id: "claim-1",
      status: "PENDING",
    } as Awaited<ReturnType<typeof claimPayment>>);
    const user = userEvent.setup();
    renderWithProviders(
      <InstallmentDetailDialog
        loanId="loan-1"
        installment={INSTALLMENT}
        open
        onOpenChange={() => {}}
      />,
    );

    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/already paid this/i), "Sent by MoMo");
    await user.click(within(dialog).getByRole("button", { name: "I've paid" }));

    await waitFor(() => expect(claimPayment).toHaveBeenCalledWith("inst-1", "Sent by MoMo"));
    expect(await within(dialog).findByText(/we've let the team know/i)).toBeInTheDocument();
  });

  it("surfaces the server's conflict message for a duplicate claim", async () => {
    vi.mocked(claimPayment).mockRejectedValue(
      new ApiError(409, {
        detail: "You've already told us about this payment — the team is reviewing it.",
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(
      <InstallmentDetailDialog
        loanId="loan-1"
        installment={INSTALLMENT}
        open
        onOpenChange={() => {}}
      />,
    );

    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "I've paid" }));

    expect(
      await within(dialog).findByText(/already told us about this payment/i),
    ).toBeInTheDocument();
  });

  it("offers no claim action on a settled installment", async () => {
    renderWithProviders(
      <InstallmentDetailDialog
        loanId="loan-1"
        installment={{ ...INSTALLMENT, status: "PAID", outstanding_amount: "0.00" }}
        open
        onOpenChange={() => {}}
      />,
    );

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).queryByRole("button", { name: "I've paid" })).not.toBeInTheDocument();
  });
});
