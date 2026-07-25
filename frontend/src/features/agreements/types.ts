/** Mirrors apps/agreements/serializers.py. */

export type EmailDeliveryStatus = "NOT_SENT" | "SENT" | "FAILED";

export interface Agreement {
  id: string;
  offer_id: string;
  request_number: string;
  typed_legal_name: string;
  acceptance_text_version: string;
  agreement_pdf_sha256: string;
  accepted_at: string;
  email_delivery_status: EmailDeliveryStatus;
  download_url: string;
  created_at: string;
}

export interface AcceptedLoanSummary {
  id: string;
  loan_number: string;
  status: string;
  principal: string;
  total_repayable: string;
}

/** Response of POST .../offers/{id}/accept/. */
export interface AcceptOfferResult {
  agreement: Agreement;
  loan: AcceptedLoanSummary;
}

export interface AcceptOfferPayload {
  typed_legal_name: string;
  declaration_accepted: boolean;
  signature_image: string;
}
