import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAmortizationPreview } from "@/features/amortization/use-amortization-preview";

import { AmortizationPreviewForm } from "./amortization-preview-form";

vi.mock("@/features/amortization/use-amortization-preview", () => ({
  useAmortizationPreview: vi.fn(),
}));

const mutateAsync = vi.fn();

describe("AmortizationPreviewForm", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    vi.mocked(useAmortizationPreview).mockReturnValue({
      mutateAsync,
    } as unknown as ReturnType<typeof useAmortizationPreview>);
  });

  it("rejects an invalid term count before calling the API", async () => {
    const user = userEvent.setup();
    render(<AmortizationPreviewForm />);

    await user.type(screen.getByLabelText(/principal/i), "10000");
    await user.type(screen.getByLabelText(/interest rate/i), "12");
    await user.clear(screen.getByLabelText(/term count/i));
    await user.type(screen.getByLabelText(/term count/i), "0");
    await user.type(screen.getByLabelText(/first due date/i), "2026-09-01");
    await user.click(screen.getByRole("button", { name: /calculate schedule/i }));

    expect(await screen.findByText(/at least 1/i)).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("renders the formatted schedule after a successful calculation", async () => {
    mutateAsync.mockResolvedValue({
      total_interest: "1200.00",
      total_repayable: "11200.00",
      installment_count: 2,
      installments: [
        {
          sequence_number: 1,
          due_date: "2026-09-01",
          principal_due: "5000.00",
          interest_due: "600.00",
          total_due: "5600.00",
        },
        {
          sequence_number: 2,
          due_date: "2026-10-01",
          principal_due: "5000.00",
          interest_due: "600.00",
          total_due: "5600.00",
        },
      ],
    });
    const user = userEvent.setup();
    render(<AmortizationPreviewForm />);

    await user.type(screen.getByLabelText(/principal/i), "10000");
    await user.type(screen.getByLabelText(/interest rate/i), "12");
    await user.clear(screen.getByLabelText(/term count/i));
    await user.type(screen.getByLabelText(/term count/i), "2");
    await user.type(screen.getByLabelText(/first due date/i), "2026-09-01");
    await user.click(screen.getByRole("button", { name: /calculate schedule/i }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("GHS 1,200.00")).toBeInTheDocument();
    expect(screen.getByText("GHS 11,200.00")).toBeInTheDocument();
    expect(screen.getAllByText("GHS 5,600.00")).toHaveLength(2);
  });
});
