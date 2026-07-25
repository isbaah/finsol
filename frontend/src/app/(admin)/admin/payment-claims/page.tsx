"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  usePaymentClaims,
  useResolvePaymentClaim,
} from "@/features/repayments/use-repayments";
import { formatDate, formatDateTime, formatGHS } from "@/lib/format";

/** The queue behind the customer "I've paid" action: every claim a customer
 * has raised, newest first. Recording the actual repayment on the loan page
 * auto-resolves its claim; "Mark reviewed" is for claims where no payment
 * ever arrives. */
export default function PaymentClaimsPage() {
  const [status, setStatus] = useState<"PENDING" | "RESOLVED" | "">("PENDING");
  const { data, isLoading, isError } = usePaymentClaims(status || undefined);
  const resolve = useResolvePaymentClaim();

  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Payment claims</h1>
        <p className="text-muted-foreground text-sm">
          Customers who say they&apos;ve paid. Verify the money arrived, then record the repayment
          on the loan — that resolves the claim automatically.
        </p>
      </div>

      <Select
        value={status}
        onChange={(event) => setStatus(event.target.value as "PENDING" | "RESOLVED" | "")}
        className="max-w-48"
      >
        <option value="PENDING">Pending</option>
        <option value="RESOLVED">Resolved</option>
        <option value="">All</option>
      </Select>

      {isLoading && <Skeleton className="h-24 w-full" />}
      {isError && (
        <p className="text-destructive text-sm">Couldn&apos;t load claims. Please try again.</p>
      )}
      {!isLoading && !isError && data?.results.length === 0 && (
        <p className="text-muted-foreground text-sm">
          {status === "PENDING" ? "No claims waiting for review." : "No claims match this filter."}
        </p>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Loan</th>
                <th className="px-5 py-3 font-medium">Installment</th>
                <th className="px-5 py-3 font-medium">Due date</th>
                <th className="px-5 py-3 font-medium">Outstanding</th>
                <th className="px-5 py-3 font-medium">Note</th>
                <th className="px-5 py-3 font-medium">Claimed</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((claim) => (
                <tr
                  key={claim.id}
                  className="border-border hover:bg-muted/60 border-b transition-colors last:border-0"
                >
                  <td className="px-5 py-3">{claim.customer_name || claim.customer_email}</td>
                  <td className="px-5 py-3">{claim.loan_number}</td>
                  <td className="px-5 py-3">#{claim.sequence_number}</td>
                  <td className="px-5 py-3">{formatDate(claim.due_date)}</td>
                  <td className="px-5 py-3">{formatGHS(claim.outstanding_amount)}</td>
                  <td className="text-muted-foreground max-w-56 truncate px-5 py-3">
                    {claim.note || "—"}
                  </td>
                  <td className="px-5 py-3">{formatDateTime(claim.created_at)}</td>
                  <td className="px-5 py-3">
                    <span
                      className={
                        claim.status === "PENDING"
                          ? "text-amber-700 dark:text-amber-400"
                          : "text-emerald-700 dark:text-emerald-400"
                      }
                    >
                      {claim.status === "PENDING" ? "Pending" : "Resolved"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/admin/loans/${claim.loan_id}`}
                        className="text-primary hover:underline"
                      >
                        View loan
                      </Link>
                      {claim.status === "PENDING" && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={resolve.isPending}
                          onClick={() => resolve.mutate(claim.id)}
                        >
                          Mark reviewed
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
