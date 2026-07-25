import { LOAN_REQUEST_STATUS_LABEL, statusBadgeClassName } from "@/features/loan-requests/status";
import type { LoanRequestStatus } from "@/features/loan-requests/types";
import { cn } from "@/lib/utils";

export function StatusBadge({
  status,
  className,
}: {
  status: LoanRequestStatus;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        statusBadgeClassName(status),
        className,
      )}
    >
      {LOAN_REQUEST_STATUS_LABEL[status]}
    </span>
  );
}
