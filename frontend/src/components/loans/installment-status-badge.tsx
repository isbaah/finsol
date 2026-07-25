import {
  INSTALLMENT_STATUS_LABEL,
  installmentStatusBadgeClassName,
  type InstallmentStatus,
} from "@/features/loans/status";
import { cn } from "@/lib/utils";

export function InstallmentStatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const known = status in INSTALLMENT_STATUS_LABEL;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        known ? installmentStatusBadgeClassName(status as InstallmentStatus) : "bg-muted",
        className,
      )}
    >
      {known ? INSTALLMENT_STATUS_LABEL[status as InstallmentStatus] : status}
    </span>
  );
}
