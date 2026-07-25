"use client";

import Link from "next/link";

import { CustomerLoanSummary } from "@/components/dashboard/customer-loan-summary";
import { StatusBadge } from "@/components/requests/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoanRequests } from "@/features/loan-requests/use-loan-requests";
import { useCustomerLoans } from "@/features/loans/use-loans";
import { formatGHS } from "@/lib/format";

const IN_FLIGHT_STATUSES = [
  "SUBMITTED",
  "UNDER_REVIEW",
  "OFFER_SENT",
  "REVISION_REQUESTED",
  "CUSTOMER_ACCEPTED",
];

/** The most relevant loan to summarise: a loan being repaid beats a loan
 * in the approval pipeline, which beats a finished one. */
const LOAN_PRIORITY = ["OVERDUE", "ACTIVE", "DISBURSED", "APPROVED_FOR_DISBURSEMENT", "PENDING_APPROVAL", "PAID_OFF"];

export default function CustomerDashboardPage() {
  const { data, isLoading } = useLoanRequests();
  const { data: loans, isLoading: loansLoading } = useCustomerLoans();
  const inFlight = data?.results.find((request) => IN_FLIGHT_STATUSES.includes(request.status));

  const currentLoan = [...(loans?.results ?? [])].sort(
    (a, b) => LOAN_PRIORITY.indexOf(a.status) - LOAN_PRIORITY.indexOf(b.status),
  )[0];

  const anythingLoading = isLoading || loansLoading;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-foreground text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="text-muted-foreground text-sm">
            Your loan, repayments, and requests at a glance.
          </p>
        </div>
        {!anythingLoading && !inFlight && (
          <Button nativeButton={false} render={<Link href="/requests/new">Request a loan</Link>} />
        )}
      </div>

      {anythingLoading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {!anythingLoading && inFlight && (
        <Card size="sm">
          <CardContent className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <p className="text-muted-foreground text-xs">Your current request</p>
              <StatusBadge status={inFlight.status} />
            </div>
            <p className="text-foreground text-sm font-medium">{inFlight.request_number}</p>
            {inFlight.current_offer && (
              <p className="text-muted-foreground text-sm">
                Offer ready: {formatGHS(inFlight.current_offer.principal)} over{" "}
                {inFlight.current_offer.installment_count} installments.
              </p>
            )}
            <div className="flex gap-2">
              <Button
                size="sm"
                nativeButton={false}
                render={<Link href={`/requests/${inFlight.id}`}>View request</Link>}
              />
              {inFlight.current_offer && (
                <Button
                  size="sm"
                  variant="outline"
                  nativeButton={false}
                  render={<Link href={`/offers/${inFlight.current_offer.id}`}>View offer</Link>}
                />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {!anythingLoading && currentLoan && <CustomerLoanSummary loan={currentLoan} />}

      {!anythingLoading && !inFlight && !currentLoan && (
        <Card size="sm">
          <CardContent className="flex flex-col items-start gap-2 py-6">
            <p className="text-foreground text-sm font-medium">No loans yet</p>
            <p className="text-muted-foreground text-sm">
              Request a loan and we&apos;ll review it — final terms are set by the administrator.
            </p>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
