"use client";

import Link from "next/link";

import { ManualReminderButton } from "@/components/messaging/manual-reminder-button";
import { Skeleton } from "@/components/ui/skeleton";
import { useUpcomingRepayments } from "@/features/dashboards/use-dashboards";
import { formatDate, formatGHS } from "@/lib/format";

function daysRemainingLabel(days: number) {
  if (days === 0) return "Due today";
  if (days === 1) return "1 day";
  return `${days} days`;
}

/** Section 16's upcoming-repayments table: installments due in fewer than
 * seven days, with per-row actions. "Record payment" opens the loan page,
 * where the Stage 10 payment modal lives — the backend stays the only place
 * that allocates money. */
export function UpcomingRepaymentsTable() {
  const { data, isLoading, isError } = useUpcomingRepayments();

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-foreground text-base font-semibold tracking-tight">Upcoming repayments (next 7 days)</h2>

      {isLoading && <Skeleton className="h-24 w-full" />}
      {isError && (
        <p className="text-destructive text-sm">
          Couldn&apos;t load upcoming repayments. Please try again.
        </p>
      )}
      {!isLoading && !isError && data?.length === 0 && (
        <p className="text-muted-foreground text-sm">
          No installments fall due in the next seven days.
        </p>
      )}

      {!isLoading && !isError && data && data.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Loan</th>
                <th className="px-5 py-3 font-medium">Amount due</th>
                <th className="px-5 py-3 font-medium">Outstanding</th>
                <th className="px-5 py-3 font-medium">Due date</th>
                <th className="px-5 py-3 font-medium">Days remaining</th>
                <th className="px-5 py-3 font-medium">Last SMS</th>
                <th className="px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.installment_id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                  <td className="px-5 py-3">{row.customer_name}</td>
                  <td className="px-5 py-3">{row.loan_number}</td>
                  <td className="px-5 py-3">{formatGHS(row.total_due)}</td>
                  <td className="px-5 py-3">{formatGHS(row.outstanding_amount)}</td>
                  <td className="px-5 py-3">{formatDate(row.due_date)}</td>
                  <td className="px-5 py-3">
                    <span
                      className={
                        row.days_remaining <= 1
                          ? "text-amber-700 dark:text-amber-400"
                          : "text-foreground"
                      }
                    >
                      {daysRemainingLabel(row.days_remaining)}
                    </span>
                  </td>
                  <td className="text-muted-foreground px-4 py-2">
                    {row.last_sms_status ?? "None sent"}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link href={`/admin/loans/${row.loan_id}`} className="text-primary hover:underline">
                        View loan
                      </Link>
                      <ManualReminderButton installmentId={row.installment_id} />
                      <Link
                        href={`/admin/sms-activity?loan=${row.loan_id}`}
                        className="text-primary hover:underline"
                      >
                        SMS history
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
