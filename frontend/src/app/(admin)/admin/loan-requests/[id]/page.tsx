"use client";

import { use, useState } from "react";

import { OfferForm } from "@/components/offers/offer-form";
import { StatusBadge } from "@/components/requests/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  useAdminLoanRequest,
  useDeclineLoanRequest,
  useStartReview,
} from "@/features/loan-requests/use-admin-loan-requests";
import { formatDateTime, formatGHS } from "@/lib/format";

const OPEN_FOR_OFFERS = ["UNDER_REVIEW", "REVISION_REQUESTED", "OFFER_SENT"];
const DECLINABLE = ["SUBMITTED", "UNDER_REVIEW"];

export default function AdminLoanRequestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: loanRequest, isLoading, isError } = useAdminLoanRequest(id);
  const startReview = useStartReview(id);
  const declineLoanRequest = useDeclineLoanRequest(id);
  const [showDeclineForm, setShowDeclineForm] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const handleStartReview = async () => {
    setActionError(null);
    try {
      await startReview.mutateAsync();
    } catch {
      setActionError("Couldn't start review — it may already have been picked up.");
    }
  };

  const handleDecline = async () => {
    if (!declineReason.trim()) return;
    setActionError(null);
    try {
      await declineLoanRequest.mutateAsync(declineReason);
      setShowDeclineForm(false);
    } catch {
      setActionError("Couldn't decline this request. Please try again.");
    }
  };

  if (isLoading) return <p className="text-muted-foreground p-6 text-sm">Loading…</p>;
  if (isError || !loanRequest) {
    return <p className="text-destructive p-6 text-sm">Couldn&apos;t load this request.</p>;
  }

  const currentDraft = loanRequest.offers.find((offer) => offer.status === "DRAFT");

  return (
    <main className="flex flex-1 flex-col gap-6 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-foreground text-2xl font-semibold tracking-tight">
            {loanRequest.request_number}
          </h1>
          <p className="text-muted-foreground text-sm">
            {loanRequest.customer_name || loanRequest.customer_email} — {loanRequest.customer_phone}
          </p>
        </div>
        <StatusBadge status={loanRequest.status} />
      </div>

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
                {loanRequest.requested_term_count}{" "}
                {loanRequest.requested_term_unit.toLowerCase()}
                {loanRequest.requested_term_count > 1 ? "s" : ""}
              </span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-muted-foreground text-sm">Submitted</span>
            <span className="text-foreground text-sm font-medium">
              {loanRequest.submitted_at ? formatDateTime(loanRequest.submitted_at) : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground text-sm">Assigned officer</span>
            <span className="text-foreground text-sm font-medium">
              {loanRequest.assigned_to_name || "Unassigned"}
            </span>
          </div>
          {"destination_masked" in loanRequest.payout_snapshot && (
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Payout</span>
              <span className="text-foreground text-sm font-medium">
                {loanRequest.payout_snapshot.method} —{" "}
                {loanRequest.payout_snapshot.destination_masked}
              </span>
            </div>
          )}
          {loanRequest.customer_notes && (
            <div>
              <span className="text-muted-foreground text-sm">Customer notes</span>
              <p className="text-foreground text-sm">{loanRequest.customer_notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        {loanRequest.status === "SUBMITTED" && (
          <Button onClick={handleStartReview} disabled={startReview.isPending}>
            {startReview.isPending ? "Starting…" : "Start review"}
          </Button>
        )}
        {DECLINABLE.includes(loanRequest.status) && !showDeclineForm && (
          <Button variant="destructive" onClick={() => setShowDeclineForm(true)}>
            Decline
          </Button>
        )}
      </div>

      {showDeclineForm && (
        <Card size="sm" className="max-w-md">
          <CardContent className="flex flex-col gap-2">
            <Textarea
              placeholder="Reason for declining (shown in the audit trail)"
              value={declineReason}
              onChange={(event) => setDeclineReason(event.target.value)}
              rows={2}
            />
            <div className="flex gap-2">
              <Button
                variant="destructive"
                onClick={handleDecline}
                disabled={declineLoanRequest.isPending || !declineReason.trim()}
              >
                Confirm decline
              </Button>
              <Button variant="outline" onClick={() => setShowDeclineForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {actionError && <p className="text-destructive text-sm">{actionError}</p>}

      {loanRequest.offers.length > 0 && (
        <div>
          <h2 className="text-foreground mb-2 text-base font-semibold tracking-tight">Offer versions</h2>
          <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-border text-muted-foreground border-b text-left">
                  <th className="px-5 py-3 font-medium">Version</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Principal</th>
                  <th className="px-5 py-3 font-medium">Total repayable</th>
                  <th className="px-5 py-3 font-medium">Sent</th>
                </tr>
              </thead>
              <tbody>
                {loanRequest.offers.map((offer) => (
                  <tr key={offer.id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                    <td className="px-5 py-3">v{offer.version_number}</td>
                    <td className="px-5 py-3">{offer.status}</td>
                    <td className="px-5 py-3">{formatGHS(offer.principal)}</td>
                    <td className="px-5 py-3">{formatGHS(offer.total_repayable)}</td>
                    <td className="px-5 py-3">
                      {offer.sent_at ? formatDateTime(offer.sent_at) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {OPEN_FOR_OFFERS.includes(loanRequest.status) && (
        <div>
          <h2 className="text-foreground mb-2 text-base font-semibold tracking-tight">
            {currentDraft ? "Edit draft offer" : "Create an offer"}
          </h2>
          <OfferForm loanRequestId={loanRequest.id} offerId={currentDraft?.id} />
        </div>
      )}
    </main>
  );
}
