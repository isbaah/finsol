/** Mirrors apps/loan_offers/serializers.py's Amortization*Serializer. */

export type TermUnit = "WEEK" | "MONTH";

export interface AmortizationPreviewRequest {
  principal: string;
  interest_rate_percent: string;
  term_count: number;
  term_unit: TermUnit;
  first_due_date: string;
}

export interface AmortizationInstallment {
  sequence_number: number;
  due_date: string;
  principal_due: string;
  interest_due: string;
  total_due: string;
}

export interface AmortizationPreviewResponse {
  total_interest: string;
  total_repayable: string;
  installment_count: number;
  installments: AmortizationInstallment[];
}
