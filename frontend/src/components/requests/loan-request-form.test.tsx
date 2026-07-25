import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useMyProfile } from "@/features/profile/use-profile";
import { useCreateLoanRequest } from "@/features/loan-requests/use-loan-requests";

import { LoanRequestForm } from "./loan-request-form";

vi.mock("@/features/profile/use-profile", () => ({
  useMyProfile: vi.fn(),
}));

vi.mock("@/features/loan-requests/use-loan-requests", () => ({
  useCreateLoanRequest: vi.fn(),
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const mutateAsync = vi.fn();

describe("LoanRequestForm", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    push.mockReset();
    vi.mocked(useMyProfile).mockReturnValue({
      data: {
        preferred_disbursement_method: "MOBILE_MONEY",
        mobile_money_number: "0241234567",
      },
    } as unknown as ReturnType<typeof useMyProfile>);
    vi.mocked(useCreateLoanRequest).mockReturnValue({
      mutateAsync,
    } as unknown as ReturnType<typeof useCreateLoanRequest>);
  });

  it("requires the accuracy declaration before submitting", async () => {
    const user = userEvent.setup();
    render(<LoanRequestForm />);

    await user.type(screen.getByLabelText(/requested amount/i), "2500");
    await user.type(screen.getByLabelText(/loan purpose/i), "School fees");
    await user.click(screen.getByRole("button", { name: /submit request/i }));

    expect(await screen.findByText(/confirm the information/i)).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("submits the payload and redirects to the new request on success", async () => {
    mutateAsync.mockResolvedValue({ id: "req-123" });
    const user = userEvent.setup();
    render(<LoanRequestForm />);

    await user.type(screen.getByLabelText(/requested amount/i), "2500");
    await user.type(screen.getByLabelText(/loan purpose/i), "School fees");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /submit request/i }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        requested_amount: "2500",
        purpose: "School fees",
      }),
    );
    await waitFor(() => expect(push).toHaveBeenCalledWith("/requests/req-123"));
  });
});
