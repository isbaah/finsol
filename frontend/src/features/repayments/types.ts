/** Mirrors apps/repayments/serializers.py. */

export type PaymentMethod = "MOBILE_MONEY" | "BANK" | "CASH" | "OTHER";
export type PaymentStatus = "POSTED" | "REVERSED";

export interface PaymentAllocation {
  installment_sequence_number: number;
  principal_amount: string;
  interest_amount: string;
  total_amount: string;
}

/** Mirrors PaymentSerializer (staff) — CustomerPaymentSerializer is the
 * same shape minus `recorded_by_name`/`allocations`/`reversal_reason`, so
 * the frontend just treats all those fields as optional on read. */
export interface Payment {
  id: string;
  receipt_number: string;
  amount: string;
  payment_date: string;
  payment_method: PaymentMethod;
  external_transaction_reference?: string;
  notes?: string;
  status: PaymentStatus;
  reversal_reason?: string;
  recorded_by_name?: string;
  recorded_at?: string;
  allocations?: PaymentAllocation[];
  created_at: string;
}

/** Mirrors PaymentClaimSerializer — the customer "I've paid" notice. */
export interface PaymentClaim {
  id: string;
  loan_id: string;
  loan_number: string;
  sequence_number: number;
  due_date: string;
  outstanding_amount: string;
  customer_name: string;
  customer_email: string;
  note: string;
  status: "PENDING" | "RESOLVED";
  resolved_by_name: string;
  resolved_at: string | null;
  created_at: string;
}

/** Mirrors RepaymentAccountSerializer — the company collection account
 * customers pay repayments into. Receiving details, deliberately unmasked. */
export interface RepaymentAccount {
  mobile_money_network: string;
  mobile_money_number: string;
  mobile_money_account_name: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
  payment_instructions: string;
  updated_at: string;
}

export type RepaymentAccountPayload = Omit<RepaymentAccount, "updated_at">;

/** POST /api/v1/admin/loans/{id}/repayments/ body — multipart when
 * `evidence_file` is present, JSON otherwise. */
export interface RecordPaymentPayload {
  amount: string;
  payment_date: string;
  payment_method: PaymentMethod;
  external_transaction_reference?: string;
  notes?: string;
  evidence_file?: File | null;
  idempotency_key?: string;
}
