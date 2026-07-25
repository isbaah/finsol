"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Payment } from "@/features/repayments/types";
import { useReversePayment } from "@/features/repayments/use-repayments";
import { formatDate, formatGHS } from "@/lib/format";
import { reversalSchema, type ReversalFormValues } from "@/schemas/repayment";

/** Section 16/19: payment history with an explicit, reason-required
 * reversal action. `showActions` distinguishes the admin page (reversal
 * available; the acting role is re-checked server-side regardless) from
 * the customer's own read-only view. */
export function PaymentHistoryTable({
  loanId,
  payments,
  showActions,
}: {
  loanId: string;
  payments: Payment[];
  showActions: boolean;
}) {
  const reversePayment = useReversePayment(loanId);
  const [target, setTarget] = useState<Payment | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ReversalFormValues>({ resolver: zodResolver(reversalSchema) });

  const onSubmit = async (values: ReversalFormValues) => {
    if (!target) return;
    setError(null);
    try {
      await reversePayment.mutateAsync({ paymentId: target.id, reason: values.reason });
      setTarget(null);
      reset();
    } catch {
      setError("Couldn't reverse this payment. Please try again.");
    }
  };

  if (payments.length === 0) {
    return <p className="text-muted-foreground text-sm">No payments recorded yet.</p>;
  }

  return (
    <>
      <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-border text-muted-foreground border-b text-left">
              <th className="px-5 py-3 font-medium">Receipt</th>
              <th className="px-5 py-3 font-medium">Date</th>
              <th className="px-5 py-3 font-medium">Amount</th>
              <th className="px-5 py-3 font-medium">Method</th>
              <th className="px-5 py-3 font-medium">Status</th>
              {showActions && <th className="px-5 py-3 font-medium">Action</th>}
            </tr>
          </thead>
          <tbody>
            {payments.map((payment) => (
              <tr key={payment.id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                <td className="px-5 py-3">{payment.receipt_number}</td>
                <td className="px-5 py-3">{formatDate(payment.payment_date)}</td>
                <td className="px-5 py-3">{formatGHS(payment.amount)}</td>
                <td className="px-5 py-3">{payment.payment_method}</td>
                <td className="px-5 py-3">
                  {payment.status === "REVERSED" ? (
                    <span className="text-red-700 dark:text-red-400">Reversed</span>
                  ) : (
                    <span className="text-emerald-700 dark:text-emerald-400">Posted</span>
                  )}
                </td>
                {showActions && (
                  <td className="px-5 py-3">
                    {payment.status === "POSTED" && (
                      <Button variant="outline" size="sm" onClick={() => setTarget(payment)}>
                        Reverse
                      </Button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog
        open={target !== null}
        onOpenChange={(next) => {
          if (!next) {
            setTarget(null);
            reset();
            setError(null);
          }
        }}
      >
        <DialogContent>
          <DialogTitle>Reverse payment {target?.receipt_number}</DialogTitle>
          <DialogDescription>
            This creates an explicit reversal record and restores the loan balance. The original
            payment record is preserved, never edited or deleted.
          </DialogDescription>
          <form onSubmit={handleSubmit(onSubmit)} className="mt-4 flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="reason">Reason</Label>
              <Textarea id="reason" rows={2} {...register("reason")} />
              {errors.reason && <p className="text-destructive text-sm">{errors.reason.message}</p>}
            </div>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <div className="flex justify-end gap-2">
              <DialogClose
                render={
                  <Button type="button" variant="outline">
                    Cancel
                  </Button>
                }
              />
              <Button type="submit" disabled={isSubmitting || reversePayment.isPending}>
                {reversePayment.isPending ? "Reversing…" : "Confirm reversal"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
