import type { LoanStatus } from "./types";

export const LOAN_STATUS_LABEL: Record<LoanStatus, string> = {
  PENDING_APPROVAL: "Pending approval",
  APPROVED_FOR_DISBURSEMENT: "Approved — awaiting disbursement",
  DISBURSED: "Disbursed",
  ACTIVE: "Active",
  PAID_OFF: "Paid off",
  OVERDUE: "Overdue",
  RESTRUCTURED: "Restructured",
  DEFAULTED: "Defaulted",
  CANCELLED: "Cancelled",
};

type StatusTone = "neutral" | "amber" | "green" | "red";

const LOAN_STATUS_TONE: Record<LoanStatus, StatusTone> = {
  PENDING_APPROVAL: "amber",
  APPROVED_FOR_DISBURSEMENT: "amber",
  DISBURSED: "green",
  ACTIVE: "green",
  PAID_OFF: "green",
  OVERDUE: "red",
  RESTRUCTURED: "red",
  DEFAULTED: "red",
  CANCELLED: "neutral",
};

const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "bg-muted text-muted-foreground",
  amber: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-400",
  green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-400",
  red: "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-400",
};

export function loanStatusBadgeClassName(status: LoanStatus): string {
  return TONE_CLASSES[LOAN_STATUS_TONE[status]];
}

/** RepaymentInstallment statuses (Stage 12: consistent badge mappings —
 * previously rendered as raw enum text in schedule tables). */
export type InstallmentStatus =
  | "UPCOMING"
  | "DUE"
  | "PARTIALLY_PAID"
  | "PAID"
  | "OVERDUE"
  | "WAIVED";

export const INSTALLMENT_STATUS_LABEL: Record<InstallmentStatus, string> = {
  UPCOMING: "Upcoming",
  DUE: "Due",
  PARTIALLY_PAID: "Partially paid",
  PAID: "Paid",
  OVERDUE: "Overdue",
  WAIVED: "Waived",
};

const INSTALLMENT_STATUS_TONE: Record<InstallmentStatus, StatusTone> = {
  UPCOMING: "neutral",
  DUE: "amber",
  PARTIALLY_PAID: "amber",
  PAID: "green",
  OVERDUE: "red",
  WAIVED: "neutral",
};

export function installmentStatusBadgeClassName(status: InstallmentStatus): string {
  return TONE_CLASSES[INSTALLMENT_STATUS_TONE[status]];
}
