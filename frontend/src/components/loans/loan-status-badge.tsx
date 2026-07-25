import { LOAN_STATUS_LABEL, loanStatusBadgeClassName } from "@/features/loans/status";
import type { LoanStatus } from "@/features/loans/types";
import { cn } from "@/lib/utils";

export function LoanStatusBadge({ status, className }: { status: LoanStatus; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        loanStatusBadgeClassName(status),
        className,
      )}
    >
      {LOAN_STATUS_LABEL[status]}
    </span>
  );
}
