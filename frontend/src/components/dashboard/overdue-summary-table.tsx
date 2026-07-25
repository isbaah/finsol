"use client";

import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { useOverdueSummary } from "@/features/dashboards/use-dashboards";
import { formatGHS } from "@/lib/format";

/** Section 16's overdue table: age buckets (1–7, 8–30, 31–60, 61+ days)
 * with installment/loan counts and outstanding totals. */
export function OverdueSummaryTable() {
  const { data, isLoading, isError } = useOverdueSummary();

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h2 className="text-foreground text-base font-semibold tracking-tight">Overdue by age</h2>
        <Link href="/admin/loans?status=OVERDUE" className="text-primary text-sm hover:underline">
          View overdue loans
        </Link>
      </div>

      {isLoading && <Skeleton className="h-24 w-full" />}
      {isError && (
        <p className="text-destructive text-sm">
          Couldn&apos;t load the overdue summary. Please try again.
        </p>
      )}
      {!isLoading && !isError && data && Number(data.total_outstanding) === 0 && (
        <p className="text-muted-foreground text-sm">Nothing is overdue. Well done.</p>
      )}

      {!isLoading && !isError && data && Number(data.total_outstanding) > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Age</th>
                <th className="px-5 py-3 font-medium">Installments</th>
                <th className="px-5 py-3 font-medium">Loans</th>
                <th className="px-5 py-3 font-medium">Outstanding</th>
              </tr>
            </thead>
            <tbody>
              {data.buckets.map((bucket) => (
                <tr key={bucket.label} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                  <td className="px-5 py-3">{bucket.label}</td>
                  <td className="px-5 py-3">{bucket.installment_count}</td>
                  <td className="px-5 py-3">{bucket.loan_count}</td>
                  <td className="px-5 py-3 text-red-700 dark:text-red-400">
                    {formatGHS(bucket.outstanding_total)}
                  </td>
                </tr>
              ))}
              <tr className="border-border bg-muted/50 border-t font-medium">
                <td className="px-5 py-3">Total</td>
                <td className="px-5 py-3" colSpan={2} />
                <td className="px-5 py-3 text-red-700 dark:text-red-400">
                  {formatGHS(data.total_outstanding)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
