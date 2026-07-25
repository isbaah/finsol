import { forwardRef, useImperativeHandle } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { acceptOffer, rejectOffer, requestOfferRevision } from "@/features/agreements/api";
import type { CustomerOffer } from "@/features/offers/types";

import { OfferDecisionPanel } from "./offer-decision-panel";

vi.mock("@/features/agreements/api", () => ({
  acceptOffer: vi.fn(),
  rejectOffer: vi.fn(),
  requestOfferRevision: vi.fn(),
  getAgreement: vi.fn(),
  retryAgreementEmail: vi.fn(),
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const { toDataURLMock } = vi.hoisted(() => ({ toDataURLMock: vi.fn() }));

vi.mock("@/components/agreements/signature-canvas", () => ({
  SignatureCanvas: forwardRef(function SignatureCanvasStub(
    _props: { onChange?: () => void },
    ref: React.Ref<{ toDataURL: () => string | null; clear: () => void }>,
  ) {
    useImperativeHandle(ref, () => ({ toDataURL: toDataURLMock, clear: vi.fn() }));
    return <div data-testid="signature-canvas-stub" />;
  }),
}));

const SENT_OFFER: CustomerOffer = {
  id: "offer-1",
  request_number: "REQ-2026-000001",
  loan_request_id: "request-1",
  version_number: 1,
  status: "SENT",
  principal: "5000.00",
  interest_rate_percent: "12.00",
  term_count: 6,
  term_unit: "MONTH",
  first_due_date: "2026-09-01",
  total_interest: "600.00",
  total_repayable: "5600.00",
  installment_count: 6,
  offer_expiry_date: null,
  customer_terms: "",
  sent_at: "2026-07-01T00:00:00Z",
  installments: [],
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("OfferDecisionPanel", () => {
  beforeEach(() => {
    vi.mocked(acceptOffer).mockReset();
    vi.mocked(rejectOffer).mockReset();
    vi.mocked(requestOfferRevision).mockReset();
    push.mockReset();
    toDataURLMock.mockReset();
  });

  it("renders nothing once the offer is no longer awaiting a decision", () => {
    renderWithProviders(<OfferDecisionPanel offer={{ ...SENT_OFFER, status: "ACCEPTED" }} />);

    expect(screen.queryByRole("button", { name: /accept offer/i })).not.toBeInTheDocument();
  });

  it("requires a drawn signature before opening the confirmation dialog", async () => {
    toDataURLMock.mockReturnValue(null);
    const user = userEvent.setup();
    renderWithProviders(<OfferDecisionPanel offer={SENT_OFFER} />);

    await user.click(screen.getByRole("button", { name: /^accept offer$/i }));
    await user.type(screen.getByLabelText(/typed full legal name/i), "Ama Owusu");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /review and accept/i }));

    expect(await screen.findByText(/draw your signature/i)).toBeInTheDocument();
    expect(screen.queryByText(/confirm loan acceptance/i)).not.toBeInTheDocument();
    expect(acceptOffer).not.toHaveBeenCalled();
  }, 15000); // Dialog + Checkbox + multi-field form fill genuinely exceeds Vitest's 5s default here.

  it("accepts the offer after confirmation and redirects to the new loan", async () => {
    toDataURLMock.mockReturnValue("data:image/png;base64,AAAA");
    vi.mocked(acceptOffer).mockResolvedValue({
      agreement: {
        id: "agreement-1",
        offer_id: "offer-1",
        request_number: "REQ-2026-000001",
        typed_legal_name: "Ama Owusu",
        acceptance_text_version: "v1",
        agreement_pdf_sha256: "abc123",
        accepted_at: "2026-07-01T00:00:00Z",
        email_delivery_status: "SENT",
        download_url: "http://localhost:8000/api/v1/agreements/agreement-1/download/",
        created_at: "2026-07-01T00:00:00Z",
      },
      loan: {
        id: "loan-1",
        loan_number: "LN-2026-000001",
        status: "PENDING_APPROVAL",
        principal: "5000.00",
        total_repayable: "5600.00",
      },
    });
    const user = userEvent.setup();
    renderWithProviders(<OfferDecisionPanel offer={SENT_OFFER} />);

    await user.click(screen.getByRole("button", { name: /^accept offer$/i }));
    await user.type(screen.getByLabelText(/typed full legal name/i), "Ama Owusu");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /review and accept/i }));

    expect(await screen.findByText(/confirm loan acceptance/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /confirm acceptance/i }));

    await waitFor(() => expect(acceptOffer).toHaveBeenCalledTimes(1));
    expect(acceptOffer).toHaveBeenCalledWith(
      "offer-1",
      expect.objectContaining({
        typed_legal_name: "Ama Owusu",
        declaration_accepted: true,
        signature_image: "data:image/png;base64,AAAA",
      }),
    );
    await waitFor(() => expect(push).toHaveBeenCalledWith("/loans/loan-1"));
  }, 15000);

  it("rejects the offer with a reason and returns to the request", async () => {
    vi.mocked(rejectOffer).mockResolvedValue({ ...SENT_OFFER, status: "REJECTED" });
    const user = userEvent.setup();
    renderWithProviders(<OfferDecisionPanel offer={SENT_OFFER} />);

    await user.click(screen.getByRole("button", { name: /reject offer/i }));
    await user.type(screen.getByLabelText(/reason/i), "Found a better rate");
    await user.click(screen.getByRole("button", { name: /confirm decline/i }));

    await waitFor(() => expect(rejectOffer).toHaveBeenCalledWith("offer-1", "Found a better rate"));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/requests/request-1"));
  });

  it("requires a reason before a revision can be requested", async () => {
    const user = userEvent.setup();
    renderWithProviders(<OfferDecisionPanel offer={SENT_OFFER} />);

    await user.click(screen.getByRole("button", { name: /request revision/i }));

    expect(screen.getByRole("button", { name: /request revision/i })).toBeDisabled();
    expect(requestOfferRevision).not.toHaveBeenCalled();
  });
});
