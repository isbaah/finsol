/** Mirrors apps/loan_offers/serializers.py's Offer*/

import type { AmortizationInstallment, TermUnit } from "@/features/amortization/types";

export type OfferStatus = "DRAFT" | "SENT" | "SUPERSEDED" | "ACCEPTED" | "REJECTED" | "EXPIRED";

/** POST .../offers/ and PATCH admin/offers/{id}/ body — mirrors
 * OfferWriteSerializer. Totals/installments are never sent by the client;
 * the backend always recomputes them via calculate(). */
export interface OfferWritePayload {
  principal: string;
  interest_rate_percent: string;
  term_count: number;
  term_unit: TermUnit;
  first_due_date: string;
  offer_expiry_date?: string | null;
  customer_terms?: string;
  internal_notes?: string;
}

/** Mirrors AdminOfferDetailSerializer — every field, staff-only. */
export interface AdminOfferDetail {
  id: string;
  loan_request: string;
  version_number: number;
  status: OfferStatus;
  principal: string;
  interest_method: string;
  interest_rate_percent: string;
  term_count: number;
  term_unit: TermUnit;
  first_due_date: string;
  total_interest: string;
  total_repayable: string;
  installment_count: number;
  offer_expiry_date: string | null;
  customer_terms: string;
  internal_notes: string;
  created_by_name: string;
  sent_at: string | null;
  accepted_at: string | null;
  installments: AmortizationInstallment[];
  created_at: string;
  updated_at: string;
}

/** Mirrors CustomerOfferSerializer — never includes internal_notes/created_by. */
export interface CustomerOffer {
  id: string;
  request_number: string;
  loan_request_id: string;
  version_number: number;
  status: OfferStatus;
  principal: string;
  interest_rate_percent: string;
  term_count: number;
  term_unit: TermUnit;
  first_due_date: string;
  total_interest: string;
  total_repayable: string;
  installment_count: number;
  offer_expiry_date: string | null;
  customer_terms: string;
  sent_at: string | null;
  installments: AmortizationInstallment[];
}
