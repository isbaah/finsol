import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useMyProfile, useSaveProfile } from "@/features/profile/use-profile";

import { ProfileForm } from "./profile-form";

vi.mock("@/features/profile/use-profile", () => ({
  useMyProfile: vi.fn(),
  useSaveProfile: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

const mutateAsync = vi.fn();

describe("ProfileForm", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    vi.mocked(useMyProfile).mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof useMyProfile>);
    vi.mocked(useSaveProfile).mockReturnValue({
      mutateAsync,
    } as unknown as ReturnType<typeof useSaveProfile>);
  });

  it("requires mobile money fields before submitting, since that's the default method", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.type(screen.getByLabelText(/first name/i), "Ama");
    await user.type(screen.getByLabelText(/last name/i), "Owusu");
    await user.type(screen.getByLabelText(/phone number/i), "0241234567");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /complete profile/i }));

    // Note the trailing period: the placeholder <option>Select a network</option>
    // has no period, so this pattern targets only the rendered error message.
    expect(await screen.findByText(/select a network\./i)).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("switches to bank fields and submits without declaration in the payload", async () => {
    const user = userEvent.setup();
    mutateAsync.mockResolvedValue({});
    render(<ProfileForm />);

    await user.type(screen.getByLabelText(/first name/i), "Ama");
    await user.type(screen.getByLabelText(/last name/i), "Owusu");
    await user.type(screen.getByLabelText(/phone number/i), "0201234567");
    await user.selectOptions(screen.getByLabelText(/payout method/i), "BANK");
    await user.type(screen.getByLabelText(/bank name/i), "GCB Bank");
    await user.type(screen.getByLabelText(/account name/i), "Ama Owusu");
    await user.type(screen.getByLabelText(/account number/i), "1234567890");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /complete profile/i }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        phone_number_e164: "0201234567",
        preferred_disbursement_method: "BANK",
        bank_name: "GCB Bank",
        bank_account_name: "Ama Owusu",
        bank_account_number: "1234567890",
      }),
    );
    const payload = mutateAsync.mock.calls[0][0];
    expect(payload).not.toHaveProperty("declaration");
  });
});
