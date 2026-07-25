"use client";

import { use } from "react";

import { BackButton } from "@/components/shared/back-button";
import { OfferDecisionPanel } from "@/components/offers/offer-decision-panel";
import { Card, CardContent } from "@/components/ui/card";
import { useCustomerOffer } from "@/features/offers/use-customer-offer";
import { formatDate, formatGHS } from "@/lib/format";

export default function CustomerOfferPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: offer, isLoading, isError } = useCustomerOffer(id);

  if (isLoading) return <p className="text-muted-foreground p-6 text-sm">Loading…</p>;
  if (isError || !offer) {
    return <p className="text-destructive p-6 text-sm">Couldn&apos;t load this offer.</p>;
  }

  const finalDueDate = offer.installments.at(-1)?.due_date;

  return (
    <main className="flex flex-1 flex-col gap-6 p-6">
      <BackButton fallbackHref="/dashboard" label="Dashboard" />
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">
          Offer for {offer.request_number}
        </h1>
        <p className="text-muted-foreground text-sm">
          Version {offer.version_number} — total-term interest only: the rate below is applied once
          to the full principal, not compounded per period.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Principal</p>
            <p className="text-foreground text-lg font-semibold">{formatGHS(offer.principal)}</p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Interest rate</p>
            <p className="text-foreground text-lg font-semibold">{offer.interest_rate_percent}%</p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Total interest</p>
            <p className="text-foreground text-lg font-semibold">
              {formatGHS(offer.total_interest)}
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Total repayable</p>
            <p className="text-foreground text-lg font-semibold">
              {formatGHS(offer.total_repayable)}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="text-muted-foreground flex flex-wrap gap-x-8 gap-y-1 text-sm">
        <span>Installments: {offer.installment_count}</span>
        <span>First due date: {formatDate(offer.first_due_date)}</span>
        {finalDueDate && <span>Final due date: {formatDate(finalDueDate)}</span>}
      </div>

      {offer.customer_terms && (
        <Card size="sm" className="max-w-2xl">
          <CardContent>
            <p className="text-muted-foreground text-xs">Terms</p>
            <p className="text-foreground text-sm">{offer.customer_terms}</p>
          </CardContent>
        </Card>
      )}

      <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-border text-muted-foreground border-b text-left">
              <th className="px-5 py-3 font-medium">#</th>
              <th className="px-5 py-3 font-medium">Due date</th>
              <th className="px-5 py-3 font-medium">Principal</th>
              <th className="px-5 py-3 font-medium">Interest</th>
              <th className="px-5 py-3 font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {offer.installments.map((installment) => (
              <tr
                key={installment.sequence_number}
                className="border-border hover:bg-muted/60 border-b transition-colors last:border-0"
              >
                <td className="px-5 py-3">{installment.sequence_number}</td>
                <td className="px-5 py-3">{formatDate(installment.due_date)}</td>
                <td className="px-5 py-3">{formatGHS(installment.principal_due)}</td>
                <td className="px-5 py-3">{formatGHS(installment.interest_due)}</td>
                <td className="px-5 py-3 font-medium">{formatGHS(installment.total_due)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <OfferDecisionPanel offer={offer} />
    </main>
  );
}
