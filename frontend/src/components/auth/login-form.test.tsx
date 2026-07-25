import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { login } from "@/features/auth/api";

import { LoginForm } from "./login-form";

vi.mock("@/features/auth/api", () => ({
  login: vi.fn(),
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("LoginForm", () => {
  beforeEach(() => {
    vi.mocked(login).mockReset();
    push.mockReset();
  });

  it("shows validation errors instead of submitting when fields are empty", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it("submits credentials and shows a server-side error on failed login", async () => {
    vi.mocked(login).mockResolvedValue({
      status: 400,
      meta: { is_authenticated: false },
      errors: [
        {
          message: "Incorrect email or password.",
          code: "email_password_mismatch",
          param: "password",
        },
      ],
    });
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "user@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(login).toHaveBeenCalledWith("user@example.com", "wrong-password"));
    expect(await screen.findByText(/incorrect email or password/i)).toBeInTheDocument();
  });

  it("redirects to the dashboard when login conflicts with an existing session", async () => {
    vi.mocked(login).mockResolvedValue({ status: 409 });
    const user = userEvent.setup();
    renderWithProviders(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "user@example.com");
    await user.type(screen.getByLabelText(/password/i), "some-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });
});
