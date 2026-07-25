/** Mirrors apps/loans/serializers.py. */

import type { Payment } from "@/features/repayments/types";

export type LoanStatus =
  | "PENDING_APPROVAL"
  | "APPROVED_FOR_DISBURSEMENT"
  | "DISBURSED"
  | "ACTIVE"
  | "PAID_OFF"
  | "OVERDUE"
  | "RESTRUCTURED"
  | "DEFAULTED"
  | "CANCELLED";

export type DisbursementMethod = "MOBILE_MONEY" | "BANK";

/** Mirrors RepaymentInstallmentSummarySerializer. */
export interface RepaymentInstallmentSummary {
  id: string;
  sequence_number: number;
  due_date: string;
  principal_due: string;
  interest_due: string;
  total_due: string;
  amount_paid: string;
  outstanding_amount: string;
  status: string;
}

/** Mirrors CustomerLoanSerializer. */
export interface CustomerLoan {
  id: string;
  loan_number: string;
  request_number: string;
  status: LoanStatus;
  principal: string;
  total_interest: string;
  total_repayable: string;
  amount_disbursed: string;
  amount_repaid: string;
  outstanding_balance: string;
  approved_at: string | null;
  disbursed_at: string | null;
  agreement_id: string;
  installments: RepaymentInstallmentSummary[];
  payments: Payment[];
  created_at: string;
}

/** Mirrors AdminLoanListSerializer. */
export interface AdminLoanListItem {
  id: string;
  loan_number: string;
  request_number: string;
  customer_email: string;
  customer_name: string;
  status: LoanStatus;
  principal: string;
  total_repayable: string;
  amount_disbursed: string;
  outstanding_balance: string;
  approved_at: string | null;
  disbursed_at: string | null;
  created_at: string;
}

/** Mirrors DisbursementSerializer. */
export interface Disbursement {
  id: string;
  amount: string;
  method: DisbursementMethod;
  masked_payout_snapshot: { method?: string; destination_masked?: string };
  external_transaction_reference: string;
  notes: string;
  recorded_by_name: string;
  recorded_at: string;
}

/** Mirrors AdminLoanDetailSerializer. */
export interface AdminLoanDetail {
  id: string;
  loan_number: string;
  request_number: string;
  customer_email: string;
  customer_name: string;
  customer_phone: string;
  status: LoanStatus;
  principal: string;
  total_interest: string;
  total_repayable: string;
  amount_disbursed: string;
  amount_repaid: string;
  outstanding_balance: string;
  approved_by_name: string;
  approved_at: string | null;
  disbursed_at: string | null;
  closed_at: string | null;
  agreement_id: string;
  disbursement: Disbursement | null;
  installments: RepaymentInstallmentSummary[];
  payments: Payment[];
  created_at: string;
  updated_at: string;
}

/** POST /api/v1/admin/loans/{id}/disburse/ body — multipart when
 * `evidence_file` is present, JSON otherwise. */
export interface DisbursementPayload {
  amount: string;
  method: DisbursementMethod;
  external_transaction_reference?: string;
  notes?: string;
  evidence_file?: File | null;
}

/** Mirrors apps/customers/serializers.py's CustomerProfileSerializer (the
 * full, unmasked shape) — only ever returned by the audited payout-detail
 * reveal endpoint. */
export interface PayoutDetails {
  id: string;
  phone_number_e164: string;
  phone_country_code: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  country: string;
  preferred_disbursement_method: DisbursementMethod;
  mobile_money_network: string;
  mobile_money_number: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
  profile_completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminLoanListParams {
  status?: LoanStatus;
  search?: string;
  ordering?: string;
}
