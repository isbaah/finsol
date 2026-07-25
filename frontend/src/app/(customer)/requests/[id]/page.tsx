"use client";

import { use, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

import { BackButton } from "@/components/shared/back-button";
import { StatusTimeline } from "@/components/requests/status-timeline";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useCancelLoanRequest, useLoanRequest } from "@/features/loan-requests/use-loan-requests";
import { formatDateTime, formatGHS } from "@/lib/format";
import { ApiError } from "@/lib/api-client";

const CANCELLABLE_STATUSES = ["DRAFT", "SUBMITTED", "UNDER_REVIEW"];

export default function LoanRequestDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: loanRequest, isLoading, isError } = useLoanRequest(id);
  const cancelLoanRequest = useCancelLoanRequest();
  const [cancelError, setCancelError] = useState<string | null>(null);

  const handleCancel = async () => {
    setCancelError(null);
    try {
      await cancelLoanRequest.mutateAsync(id);
      toast.success("Request cancelled.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setCancelError("This request can no longer be cancelled.");
        return;
      }
      setCancelError("Couldn't cancel this request. Please try again.");
    }
  };

  if (isLoading) return <p className="text-muted-foreground p-6 text-sm">Loading…</p>;
  if (isError || !loanRequest) {
    return <p className="text-destructive p-6 text-sm">Couldn&apos;t load this request.</p>;
  }

  return (
    <main className="flex flex-1 flex-col gap-6 p-6">
      <BackButton fallbackHref="/requests" label="My requests" />
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">
          {loanRequest.request_number}
        </h1>
        <p className="text-muted-foreground text-sm">
          Submitted {loanRequest.submitted_at ? formatDateTime(loanRequest.submitted_at) : "—"}
        </p>
      </div>

      <StatusTimeline status={loanRequest.status} />

      <Card size="sm" className="max-w-md">
        <CardContent className="flex flex-col gap-2">
          <div className="flex justify-between">
            <span className="text-muted-foreground text-sm">Requested amount</span>
            <span className="text-foreground text-sm font-medium">
              {formatGHS(loanRequest.requested_amount)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground text-sm">Purpose</span>
            <span className="text-foreground text-sm font-medium">{loanRequest.purpose}</span>
          </div>
          {loanRequest.requested_term_count && (
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Preferred term</span>
              <span className="text-foreground text-sm font-medium">
                {loanRequest.requested_term_count} {loanRequest.requested_term_unit.toLowerCase()}
                {loanRequest.requested_term_count > 1 ? "s" : ""}
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {loanRequest.current_offer && (
        <Card size="sm" className="max-w-md">
          <CardContent className="flex flex-col gap-2">
            <p className="text-muted-foreground text-xs">An offer is waiting for your review</p>
            <p className="text-foreground text-sm">
              {formatGHS(loanRequest.current_offer.principal)} over{" "}
              {loanRequest.current_offer.installment_count} installments — total repayable{" "}
              {formatGHS(loanRequest.current_offer.total_repayable)}
            </p>
            <Button
              nativeButton={false}
              render={<Link href={`/offers/${loanRequest.current_offer.id}`}>View offer</Link>}
            />
          </CardContent>
        </Card>
      )}

      {loanRequest.loan && (
        <Card size="sm" className="max-w-md">
          <CardContent className="flex flex-col gap-2">
            <p className="text-muted-foreground text-xs">This request became a loan</p>
            <p className="text-foreground text-sm font-medium">{loanRequest.loan.loan_number}</p>
            <Button
              nativeButton={false}
              render={<Link href={`/loans/${loanRequest.loan.id}`}>View loan</Link>}
            />
          </CardContent>
        </Card>
      )}

      {CANCELLABLE_STATUSES.includes(loanRequest.status) && (
        <div className="flex flex-col items-start gap-2">
          <Button
            variant="destructive"
            onClick={handleCancel}
            disabled={cancelLoanRequest.isPending}
          >
            {cancelLoanRequest.isPending ? "Cancelling…" : "Cancel request"}
          </Button>
          {cancelError && <p className="text-destructive text-sm">{cancelError}</p>}
        </div>
      )}
    </main>
  );
}
