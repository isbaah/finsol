import { LOAN_REQUEST_STATUS_LABEL } from "@/features/loan-requests/status";
import type { LoanRequestStatus } from "@/features/loan-requests/types";
import { cn } from "@/lib/utils";

// The "happy path" a request normally walks. Statuses outside this list
// (DECLINED/CANCELLED/CUSTOMER_REJECTED/REVISION_REQUESTED) are shown as a
// distinct outcome step appended at the end instead of forcing them onto
// this line (Stage 6: "customer-facing status timeline reading straight
// off LoanRequest.status").
const HAPPY_PATH: LoanRequestStatus[] = [
  "SUBMITTED",
  "UNDER_REVIEW",
  "OFFER_SENT",
  "CUSTOMER_ACCEPTED",
  "CONVERTED_TO_LOAN",
];

const EXCEPTION_STATUSES: LoanRequestStatus[] = [
  "DECLINED",
  "CANCELLED",
  "CUSTOMER_REJECTED",
  "REVISION_REQUESTED",
];

export function StatusTimeline({ status }: { status: LoanRequestStatus }) {
  const isException = EXCEPTION_STATUSES.includes(status);
  const currentIndex = HAPPY_PATH.indexOf(status);
  const steps = isException ? [...HAPPY_PATH.slice(0, 2), status] : HAPPY_PATH;
  const reachedIndex = isException ? steps.length - 1 : currentIndex;

  return (
    <ol className="flex flex-wrap items-center gap-2" aria-label="Request status timeline">
      {steps.map((step, index) => {
        const done = index < reachedIndex;
        const active = index === reachedIndex;
        return (
          <li key={step} className="flex items-center gap-2">
            <span
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium",
                done &&
                  "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-400",
                active && !isException && "bg-primary text-primary-foreground",
                active &&
                  isException &&
                  "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-400",
                !done && !active && "bg-muted text-muted-foreground",
              )}
            >
              {LOAN_REQUEST_STATUS_LABEL[step]}
            </span>
            {index < steps.length - 1 && <span className="text-muted-foreground text-xs">→</span>}
          </li>
        );
      })}
    </ol>
  );
}
