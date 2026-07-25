"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRecentTransactions } from "@/features/dashboards/use-dashboards";
import { formatDate, formatGHS } from "@/lib/format";
import type { RecentTransactionRow } from "@/features/dashboards/types";

const TRANSACTION_LABEL: Record<RecentTransactionRow["transaction_type"], string> = {
  DISBURSEMENT: "Disbursement",
  REPAYMENT: "Repayment",
  REVERSAL: "Reversal",
  ADJUSTMENT: "Adjustment",
  WRITE_OFF: "Write-off",
};

const TRANSACTION_TONE: Record<RecentTransactionRow["transaction_type"], string> = {
  DISBURSEMENT: "text-foreground",
  REPAYMENT: "text-emerald-700 dark:text-emerald-400",
  REVERSAL: "text-red-700 dark:text-red-400",
  ADJUSTMENT: "text-muted-foreground",
  WRITE_OFF: "text-red-700 dark:text-red-400",
};

/** The dashboard's recent ledger entries, straight from the append-only
 * LoanTransaction ledger. `h-full` + internal scroll so it always matches
 * the chart card's height on the same dashboard row. */
export function RecentTransactionsPanel() {
  const { data, isLoading, isError } = useRecentTransactions();

  return (
    <Card size="sm" className="h-full">
      <CardHeader>
        <CardTitle>Recent transactions</CardTitle>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        {isLoading && <Skeleton className="h-24 w-full" />}
        {isError && (
          <p className="text-destructive text-sm">Couldn&apos;t load recent transactions.</p>
        )}
        {!isLoading && !isError && data?.length === 0 && (
          <p className="text-muted-foreground text-sm">No ledger activity yet.</p>
        )}
        {!isLoading &&
          !isError &&
          data?.map((entry) => (
            <div key={entry.id} className="flex items-center justify-between gap-3 text-sm">
              <div className="min-w-0">
                <p className={`truncate font-medium ${TRANSACTION_TONE[entry.transaction_type]}`}>
                  {TRANSACTION_LABEL[entry.transaction_type]}
                </p>
                <p className="text-muted-foreground truncate text-xs">
                  <Link href={`/admin/loans/${entry.loan_id}`} className="hover:underline">
                    {entry.loan_number}
                  </Link>{" "}
                  — {formatDate(entry.effective_date)}
                </p>
              </div>
              <span className="text-foreground shrink-0 font-medium">
                {formatGHS(entry.amount)}
              </span>
            </div>
          ))}
      </CardContent>
    </Card>
  );
}

// The SMS-delivery panel that used to live here was removed from the
// dashboard by user request — those counts live on /admin/sms-activity.
