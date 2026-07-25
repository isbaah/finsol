/** Mirrors apps/dashboards/views.py. Money is always a string, matching the
 * rest of the API. */

export interface DashboardMetrics {
  outstanding_portfolio_balance: string;
  amount_due_this_month: string;
  amount_collected_this_month: string;
  overdue_amount: string;
  active_loans: number;
  new_request_count: number;
  pending_approval_count: number;
  awaiting_disbursement_count: number;
  pending_payment_claim_count: number;
}

export type ChartMonths = 6 | 12;

export interface CollectionsChartRow {
  /** First day of the month, ISO date ("2026-07-01"). */
  month: string;
  expected: string;
  collected: string;
}

export interface UpcomingRepaymentRow {
  installment_id: string;
  loan_id: string;
  loan_number: string;
  customer_name: string;
  sequence_number: number;
  total_due: string;
  outstanding_amount: string;
  due_date: string;
  days_remaining: number;
  status: string;
  last_sms_status: string | null;
  last_sms_type: string | null;
}

export interface OverdueBucket {
  label: string;
  min_days: number;
  max_days: number | null;
  installment_count: number;
  loan_count: number;
  outstanding_total: string;
}

export interface OverdueSummary {
  buckets: OverdueBucket[];
  total_outstanding: string;
}

export interface RecentTransactionRow {
  id: string;
  loan_id: string;
  loan_number: string;
  transaction_type: "DISBURSEMENT" | "REPAYMENT" | "REVERSAL" | "ADJUSTMENT" | "WRITE_OFF";
  amount: string;
  effective_date: string;
  created_at: string;
}
