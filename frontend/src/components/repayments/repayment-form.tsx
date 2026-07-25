"use client";

import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { AdminLoanDetail } from "@/features/loans/types";
import { useRecordPayment } from "@/features/repayments/use-repayments";
import { ApiError } from "@/lib/api-client";
import { formatDate, formatGHS } from "@/lib/format";
import { repaymentSchema, type RepaymentFormValues } from "@/schemas/repayment";

function extractErrorDetail(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return null;
}

/** Section 16's "Payment modal": shows the current outstanding balance and
 * next due installment, an amount/date/method form, and a resulting-balance
 * preview — the backend recalculates the authoritative allocation, so this
 * preview is informational only. */
export function RepaymentForm({ loan }: { loan: AdminLoanDetail }) {
  const recordPayment = useRecordPayment(loan.id);
  const [open, setOpen] = useState(false);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // Minted once per dialog session so a double-click submits the same
  // idempotency key twice — the second request is a clean no-op, not a
  // second payment (Section 20/26's double-submit protection).
  const [idempotencyKey] = useState(() => crypto.randomUUID());

  const nextInstallment = useMemo(
    () => loan.installments.find((installment) => installment.outstanding_amount !== "0.00"),
    [loan.installments],
  );

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RepaymentFormValues>({
    resolver: zodResolver(repaymentSchema),
    defaultValues: {
      amount: nextInstallment?.outstanding_amount ?? "",
      payment_date: new Date().toISOString().slice(0, 10),
      payment_method: "MOBILE_MONEY",
    },
  });

  // useWatch (not the form-level watch() function) so the React Compiler
  // can still memoize this component — see profile-form.tsx's identical
  // precedent.
  const watchedAmount = Number(useWatch({ control, name: "amount" }) || 0);
  const resultingBalance = Math.max(Number(loan.outstanding_balance) - watchedAmount, 0);

  const onSubmit = async (values: RepaymentFormValues) => {
    setSubmitError(null);
    try {
      await recordPayment.mutateAsync({
        amount: values.amount,
        payment_date: values.payment_date,
        payment_method: values.payment_method,
        external_transaction_reference: values.external_transaction_reference,
        notes: values.notes,
        evidence_file: evidenceFile,
        idempotency_key: idempotencyKey,
      });
      setOpen(false);
      reset();
      setEvidenceFile(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setSubmitError(extractErrorDetail(error.body) ?? "This payment couldn't be recorded.");
        return;
      }
      setSubmitError("Couldn't record this payment. Please try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button>Record repayment</Button>} />
      <DialogContent className="max-w-lg">
        <DialogTitle>Record repayment — {loan.loan_number}</DialogTitle>
        <DialogDescription>
          {loan.customer_name} · Outstanding balance: {formatGHS(loan.outstanding_balance)}
          {nextInstallment && (
            <>
              {" "}
              · Next due: {formatGHS(nextInstallment.outstanding_amount)} on{" "}
              {formatDate(nextInstallment.due_date)}
            </>
          )}
        </DialogDescription>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="amount">Amount received (GHS)</Label>
            <Input id="amount" inputMode="decimal" {...register("amount")} />
            {errors.amount && <p className="text-destructive text-sm">{errors.amount.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="payment_date">Payment date</Label>
            <Input id="payment_date" type="date" {...register("payment_date")} />
            {errors.payment_date && (
              <p className="text-destructive text-sm">{errors.payment_date.message}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="payment_method">Method</Label>
            <Select id="payment_method" {...register("payment_method")}>
              <option value="MOBILE_MONEY">Mobile Money</option>
              <option value="BANK">Bank</option>
              <option value="CASH">Cash</option>
              <option value="OTHER">Other</option>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="external_transaction_reference">External reference (optional)</Label>
            <Input id="external_transaction_reference" {...register("external_transaction_reference")} />
          </div>
          <div className="flex flex-col gap-1.5 sm:col-span-2">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Textarea id="notes" rows={2} {...register("notes")} />
          </div>
          <div className="flex flex-col gap-1.5 sm:col-span-2">
            <Label htmlFor="evidence_file">Payment evidence (optional)</Label>
            <input
              id="evidence_file"
              type="file"
              accept="image/*,application/pdf"
              onChange={(event) => setEvidenceFile(event.target.files?.[0] ?? null)}
              className="text-foreground text-sm"
            />
          </div>

          <div className="border-border bg-muted/40 rounded-lg border p-3 text-sm sm:col-span-2">
            <p className="text-muted-foreground">
              Applied oldest-installment-first (interest before principal). Resulting balance:{" "}
              <span className="text-foreground font-medium">{formatGHS(resultingBalance)}</span>
            </p>
          </div>

          {submitError && <p className="text-destructive text-sm sm:col-span-2">{submitError}</p>}

          <div className="flex gap-2 sm:col-span-2">
            <Button type="submit" disabled={isSubmitting || recordPayment.isPending}>
              {recordPayment.isPending ? "Recording…" : "Record repayment"}
            </Button>
            <DialogClose
              render={
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              }
            />
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
