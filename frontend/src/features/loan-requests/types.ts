/** Mirrors apps/loan_requests/serializers.py. */

export type LoanRequestStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "OFFER_SENT"
  | "CUSTOMER_ACCEPTED"
  | "CUSTOMER_REJECTED"
  | "REVISION_REQUESTED"
  | "APPROVED"
  | "DECLINED"
  | "CANCELLED"
  | "CONVERTED_TO_LOAN";

export type TermUnit = "WEEK" | "MONTH";

/** Mirrors loan_requests/serializers.py's _CurrentOfferSummarySerializer. */
export interface CurrentOfferSummary {
  id: string;
  version_number: number;
  status: string;
  principal: string;
  total_repayable: string;
  installment_count: number;
  sent_at: string;
}

/** Mirrors loan_requests/serializers.py's _LoanSummarySerializer. */
export interface LoanSummary {
  id: string;
  loan_number: string;
  status: string;
}

/** Mirrors LoanRequestSerializer — the customer's own view. */
export interface LoanRequest {
  id: string;
  request_number: string;
  requested_amount: string;
  purpose: string;
  requested_term_count: number | null;
  requested_term_unit: TermUnit | "";
  status: LoanRequestStatus;
  submitted_at: string | null;
  customer_notes: string;
  current_offer: CurrentOfferSummary | null;
  loan: LoanSummary | null;
  created_at: string;
  updated_at: string;
}

/** POST /api/v1/customer/loan-requests/ body. */
export interface LoanRequestCreatePayload {
  requested_amount: string;
  purpose: string;
  requested_term_count?: number | null;
  requested_term_unit?: TermUnit | "";
  customer_notes?: string;
}

/** Mirrors AdminLoanRequestListSerializer. */
export interface AdminLoanRequestListItem {
  id: string;
  request_number: string;
  customer_email: string;
  customer_name: string;
  requested_amount: string;
  purpose: string;
  requested_term_count: number | null;
  requested_term_unit: TermUnit | "";
  status: LoanRequestStatus;
  submitted_at: string | null;
  assigned_to_name: string;
  created_at: string;
}

/** Mirrors _OfferVersionSummarySerializer. */
export interface OfferVersionSummary {
  id: string;
  version_number: number;
  status: string;
  principal: string;
  total_repayable: string;
  created_at: string;
  sent_at: string | null;
}

/** Mirrors AdminLoanRequestDetailSerializer. */
export interface AdminLoanRequestDetail {
  id: string;
  request_number: string;
  customer_email: string;
  customer_name: string;
  customer_phone: string;
  requested_amount: string;
  purpose: string;
  requested_term_count: number | null;
  requested_term_unit: TermUnit | "";
  payout_snapshot: { method: string; destination_masked: string } | Record<string, never>;
  status: LoanRequestStatus;
  submitted_at: string | null;
  assigned_to_name: string;
  customer_notes: string;
  internal_notes: string;
  offers: OfferVersionSummary[];
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AdminLoanRequestListParams {
  status?: LoanRequestStatus;
  search?: string;
  ordering?: string;
}
