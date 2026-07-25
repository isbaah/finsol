"use client";

import { useState } from "react";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { CheckIcon, CopyIcon } from "lucide-react";

import { InstallmentStatusBadge } from "@/components/loans/installment-status-badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useClaimPayment, useRepaymentAccount } from "@/features/repayments/use-repayments";
import type { RepaymentInstallmentSummary } from "@/features/loans/types";
import { ApiError } from "@/lib/api-client";
import { formatDate, formatGHS } from "@/lib/format";

const CLAIMABLE_STATUSES = ["UPCOMING", "DUE", "PARTIALLY_PAID", "OVERDUE"];

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable (permissions/insecure context) — the number
      // is still visible to copy manually.
    }
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      aria-label={copied ? `${label} copied` : `Copy ${label}`}
      onClick={handleCopy}
    >
      {copied ? (
        <CheckIcon aria-hidden className="text-emerald-600" />
      ) : (
        <CopyIcon aria-hidden />
      )}
    </Button>
  );
}

/** Customer-side payment detail view for one installment, opened by
 * clicking a row in the schedule. "I've paid" records an informational
 * PaymentClaim the admin team reviews — no balances change until staff
 * record the actual payment. */
export function InstallmentDetailDialog({
  loanId,
  installment,
  open,
  onOpenChange,
}: {
  loanId: string;
  installment: RepaymentInstallmentSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const claimPayment = useClaimPayment(loanId);
  // Only fetched while the dialog is open — the "pay to" details set by the
  // super admin on /admin/settings.
  const { data: payTo } = useRepaymentAccount(open);
  const [note, setNote] = useState("");
  const [claimed, setClaimed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpenChange = (next: boolean) => {
    onOpenChange(next);
    if (!next) {
      setNote("");
      setClaimed(false);
      setError(null);
    }
  };

  const handleClaim = async () => {
    if (!installment) return;
    setError(null);
    try {
      await claimPayment.mutateAsync({ installmentId: installment.id, note });
      setClaimed(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const detail = (err.body as { detail?: string } | null)?.detail;
        setError(detail ?? "We couldn't record this right now. Please try again.");
        return;
      }
      setError("We couldn't record this right now. Please try again.");
    }
  };

  if (!installment) return null;
  const claimable = CLAIMABLE_STATUSES.includes(installment.status);
  const hasMobileMoney = !!payTo?.mobile_money_number;
  const hasBank = !!payTo?.bank_account_number;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogTitle>Installment #{installment.sequence_number}</DialogTitle>
        <DialogDescription>
          Due {formatDate(installment.due_date)} — payment details for this installment.
        </DialogDescription>

        <dl className="mt-4 flex flex-col gap-2 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Status</dt>
            <dd>
              <InstallmentStatusBadge status={installment.status} />
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Principal due</dt>
            <dd className="text-foreground font-medium">
              {formatGHS(installment.principal_due)}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Interest due</dt>
            <dd className="text-foreground font-medium">{formatGHS(installment.interest_due)}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Total due</dt>
            <dd className="text-foreground font-medium">{formatGHS(installment.total_due)}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Paid so far</dt>
            <dd className="font-medium text-emerald-700 dark:text-emerald-400">
              {formatGHS(installment.amount_paid)}
            </dd>
          </div>
          <div className="border-border flex items-center justify-between border-t pt-2">
            <dt className="text-muted-foreground">Left to pay</dt>
            <dd className="text-foreground text-base font-semibold">
              {formatGHS(installment.outstanding_amount)}
            </dd>
          </div>
        </dl>

        {claimable && payTo && (hasMobileMoney || hasBank) && (
          <div className="bg-muted/60 mt-4 flex flex-col gap-2 rounded-xl p-3 text-sm">
            <p className="text-foreground font-semibold">Pay to</p>
            {hasMobileMoney && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">
                  {payTo.mobile_money_network || "Mobile money"}
                  {payTo.mobile_money_account_name && ` — ${payTo.mobile_money_account_name}`}
                </span>
                <span className="flex items-center gap-1">
                  <span className="text-foreground font-medium">{payTo.mobile_money_number}</span>
                  <CopyButton value={payTo.mobile_money_number} label="mobile money number" />
                </span>
              </div>
            )}
            {hasBank && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">
                  {payTo.bank_name || "Bank"}
                  {payTo.bank_account_name && ` — ${payTo.bank_account_name}`}
                </span>
                <span className="flex items-center gap-1">
                  <span className="text-foreground font-medium">{payTo.bank_account_number}</span>
                  <CopyButton value={payTo.bank_account_number} label="bank account number" />
                </span>
              </div>
            )}
            {payTo.payment_instructions && (
              <p className="text-muted-foreground text-xs">{payTo.payment_instructions}</p>
            )}
          </div>
        )}

        {claimed ? (
          <div className="mt-4 flex flex-col gap-3">
            <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300">
              Thanks — we&apos;ve let the team know. Your balance will update once they confirm
              the payment.
            </p>
            <div className="flex justify-end">
              <DialogClose render={<Button variant="outline">Close</Button>} />
            </div>
          </div>
        ) : claimable ? (
          <div className="mt-4 flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="claim-note">Already paid this? Tell us how (optional)</Label>
              <Textarea
                id="claim-note"
                rows={2}
                placeholder="e.g. Sent GHS 300 by MTN MoMo this morning"
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </div>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <div className="flex justify-end gap-2">
              <DialogClose render={<Button variant="outline">Close</Button>} />
              <Button onClick={handleClaim} disabled={claimPayment.isPending}>
                {claimPayment.isPending ? "Sending…" : "I've paid"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-4 flex justify-end">
            <DialogClose render={<Button variant="outline">Close</Button>} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
