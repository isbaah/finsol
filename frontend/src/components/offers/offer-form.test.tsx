import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createOffer, getAdminOffer, sendOffer, updateDraftOffer } from "@/features/offers/api";
import type { AdminOfferDetail } from "@/features/offers/types";

import { OfferForm } from "./offer-form";

vi.mock("@/features/offers/api", () => ({
  createOffer: vi.fn(),
  getAdminOffer: vi.fn(),
  updateDraftOffer: vi.fn(),
  sendOffer: vi.fn(),
}));

const DRAFT_OFFER: AdminOfferDetail = {
  id: "offer-1",
  loan_request: "req-1",
  version_number: 1,
  status: "DRAFT",
  principal: "10000.00",
  interest_method: "FLAT_TOTAL_TERM",
  interest_rate_percent: "12.00",
  term_count: 6,
  term_unit: "MONTH",
  first_due_date: "2026-09-01",
  total_interest: "1200.00",
  total_repayable: "11200.00",
  installment_count: 6,
  offer_expiry_date: null,
  customer_terms: "",
  internal_notes: "",
  created_by_name: "Officer One",
  sent_at: null,
  accepted_at: null,
  installments: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("OfferForm", () => {
  beforeEach(() => {
    vi.mocked(createOffer).mockReset();
    vi.mocked(getAdminOffer).mockReset();
    vi.mocked(updateDraftOffer).mockReset();
    vi.mocked(sendOffer).mockReset();
  });

  it("rejects an invalid term count before calling the API", async () => {
    const user = userEvent.setup();
    renderWithProviders(<OfferForm loanRequestId="req-1" />);

    await user.type(screen.getByLabelText(/principal/i), "10000");
    await user.type(screen.getByLabelText(/interest rate/i), "12");
    await user.clear(screen.getByLabelText(/term count/i));
    await user.type(screen.getByLabelText(/term count/i), "0");
    await user.type(screen.getByLabelText(/first due date/i), "2026-09-01");
    await user.click(screen.getByRole("button", { name: /create draft offer/i }));

    expect(await screen.findByText(/at least 1/i)).toBeInTheDocument();
    expect(createOffer).not.toHaveBeenCalled();
  });

  it("creates a draft offer and shows a Send action", async () => {
    vi.mocked(createOffer).mockResolvedValue(DRAFT_OFFER);
    const user = userEvent.setup();
    renderWithProviders(<OfferForm loanRequestId="req-1" />);

    await user.type(screen.getByLabelText(/principal/i), "10000");
    await user.type(screen.getByLabelText(/interest rate/i), "12");
    await user.clear(screen.getByLabelText(/term count/i));
    await user.type(screen.getByLabelText(/term count/i), "6");
    await user.type(screen.getByLabelText(/first due date/i), "2026-09-01");
    await user.click(screen.getByRole("button", { name: /create draft offer/i }));

    await waitFor(() => expect(createOffer).toHaveBeenCalledTimes(1));
    expect(createOffer).toHaveBeenCalledWith(
      "req-1",
      expect.objectContaining({ principal: "10000", term_count: 6 }),
    );
    expect(
      await screen.findByRole("button", { name: /send offer to customer/i }),
    ).toBeInTheDocument();
  });

  it("sends the newly created offer's own id, not a stale one", async () => {
    vi.mocked(createOffer).mockResolvedValue(DRAFT_OFFER);
    vi.mocked(sendOffer).mockResolvedValue({ ...DRAFT_OFFER, status: "SENT" });
    const user = userEvent.setup();
    renderWithProviders(<OfferForm loanRequestId="req-1" />);

    await user.type(screen.getByLabelText(/principal/i), "10000");
    await user.type(screen.getByLabelText(/interest rate/i), "12");
    await user.clear(screen.getByLabelText(/term count/i));
    await user.type(screen.getByLabelText(/term count/i), "6");
    await user.type(screen.getByLabelText(/first due date/i), "2026-09-01");
    await user.click(screen.getByRole("button", { name: /create draft offer/i }));
    await screen.findByRole("button", { name: /send offer to customer/i });
    await user.click(screen.getByRole("button", { name: /send offer to customer/i }));

    await waitFor(() => expect(sendOffer).toHaveBeenCalledWith("offer-1"));
  });

  it("loads an existing draft for editing", async () => {
    vi.mocked(getAdminOffer).mockResolvedValue(DRAFT_OFFER);
    renderWithProviders(<OfferForm loanRequestId="req-1" offerId="offer-1" />);

    expect(await screen.findByDisplayValue("10000.00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save draft/i })).toBeInTheDocument();
  });
});
