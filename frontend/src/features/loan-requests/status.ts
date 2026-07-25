import type { LoanRequestStatus } from "./types";

/** Human label + colour tone per master prompt Section 16 ("green for
 * positive/current, amber for upcoming attention, red for overdue/failed
 * ... never rely on colour alone"). Shared by the list, detail, and
 * dashboard views so a status always reads the same way everywhere. */
export const LOAN_REQUEST_STATUS_LABEL: Record<LoanRequestStatus, string> = {
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  UNDER_REVIEW: "Under review",
  OFFER_SENT: "Offer sent",
  CUSTOMER_ACCEPTED: "Accepted",
  CUSTOMER_REJECTED: "Rejected",
  REVISION_REQUESTED: "Revision requested",
  APPROVED: "Approved",
  DECLINED: "Declined",
  CANCELLED: "Cancelled",
  CONVERTED_TO_LOAN: "Converted to loan",
};

export type StatusTone = "neutral" | "amber" | "green" | "red";

export const LOAN_REQUEST_STATUS_TONE: Record<LoanRequestStatus, StatusTone> = {
  DRAFT: "neutral",
  SUBMITTED: "amber",
  UNDER_REVIEW: "amber",
  OFFER_SENT: "amber",
  CUSTOMER_ACCEPTED: "green",
  CUSTOMER_REJECTED: "red",
  REVISION_REQUESTED: "amber",
  APPROVED: "green",
  DECLINED: "red",
  CANCELLED: "neutral",
  CONVERTED_TO_LOAN: "green",
};

const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "bg-muted text-muted-foreground",
  amber: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-400",
  green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-400",
  red: "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-400",
};

export function statusBadgeClassName(status: LoanRequestStatus): string {
  return TONE_CLASSES[LOAN_REQUEST_STATUS_TONE[status]];
}
