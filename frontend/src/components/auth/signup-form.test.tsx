import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { signup } from "@/features/auth/api";

import { SignupForm } from "./signup-form";

vi.mock("@/features/auth/api", () => ({
  signup: vi.fn(),
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("SignupForm", () => {
  beforeEach(() => {
    vi.mocked(signup).mockReset();
    push.mockReset();
  });

  it("rejects an unchecked accuracy declaration", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupForm />);

    await user.type(screen.getByLabelText(/^email$/i), "new@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "a-strong-password-1");
    await user.type(screen.getByLabelText(/confirm password/i), "a-strong-password-1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/confirm your information is accurate/i)).toBeInTheDocument();
    expect(signup).not.toHaveBeenCalled();
  });

  it("rejects mismatched passwords", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SignupForm />);

    await user.type(screen.getByLabelText(/^email$/i), "new@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "a-strong-password-1");
    await user.type(screen.getByLabelText(/confirm password/i), "does-not-match");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(signup).not.toHaveBeenCalled();
  });

  it("shows a confirmation message once signup returns a pending verification flow", async () => {
    vi.mocked(signup).mockResolvedValue({
      status: 401,
      meta: { is_authenticated: false },
      data: { flows: [{ id: "verify_email", is_pending: true }] },
    });
    const user = userEvent.setup();
    renderWithProviders(<SignupForm />);

    await user.type(screen.getByLabelText(/^email$/i), "new.customer@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "a-strong-password-1");
    await user.type(screen.getByLabelText(/confirm password/i), "a-strong-password-1");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/check your email/i)).toBeInTheDocument();
    expect(screen.getByText(/new\.customer@example\.com/)).toBeInTheDocument();
  });

  it("redirects to the dashboard when signup conflicts with an existing session", async () => {
    vi.mocked(signup).mockResolvedValue({ status: 409 });
    const user = userEvent.setup();
    renderWithProviders(<SignupForm />);

    await user.type(screen.getByLabelText(/^email$/i), "already.signed.in@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "a-strong-password-1");
    await user.type(screen.getByLabelText(/confirm password/i), "a-strong-password-1");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });
});
