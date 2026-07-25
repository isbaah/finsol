"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { usePayoutDetails } from "@/features/loans/use-loans";

/** Stage 9: "Implement authorised payout-detail reveal." Fetched only on
 * an explicit click (usePayoutDetails is `enabled: false`) — never
 * eagerly, and every fetch is audited server-side
 * (apps/loans/views.py::LoanPayoutDetailsRevealView). */
export function PayoutDetailsReveal({ loanId }: { loanId: string }) {
  const { data, refetch, isFetching, isError } = usePayoutDetails(loanId);
  const [revealed, setRevealed] = useState(false);

  const handleReveal = async () => {
    await refetch();
    setRevealed(true);
  };

  if (!revealed) {
    return (
      <Button variant="outline" size="sm" onClick={handleReveal} disabled={isFetching}>
        {isFetching ? "Loading…" : "Reveal payout details"}
      </Button>
    );
  }

  if (isError || !data) {
    return <p className="text-destructive text-sm">Couldn&apos;t load payout details.</p>;
  }

  return (
    <Card size="sm" className="max-w-sm">
      <CardContent className="flex flex-col gap-2">
        <p className="text-muted-foreground text-xs">Payout details — this view was audited</p>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Method</span>
          <span className="text-foreground font-medium">{data.preferred_disbursement_method}</span>
        </div>
        {data.preferred_disbursement_method === "MOBILE_MONEY" ? (
          <>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Network</span>
              <span className="text-foreground font-medium">{data.mobile_money_network}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Number</span>
              <span className="text-foreground font-medium">{data.mobile_money_number}</span>
            </div>
          </>
        ) : (
          <>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Bank</span>
              <span className="text-foreground font-medium">{data.bank_name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Account name</span>
              <span className="text-foreground font-medium">{data.bank_account_name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Account number</span>
              <span className="text-foreground font-medium">{data.bank_account_number}</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
