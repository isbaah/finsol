"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { AdminLoanDetail } from "@/features/loans/types";
import { useDisburseLoan } from "@/features/loans/use-loans";
import { ApiError } from "@/lib/api-client";
import { disbursementSchema, type DisbursementFormValues } from "@/schemas/disbursement";

function extractErrorDetail(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return null;
}

/** Stage 9's disbursement modal (rendered inline, not in a dialog, since
 * the surrounding page already gates it behind APPROVED_FOR_DISBURSEMENT).
 * `amount`/status/duplicate checks are all re-validated server-side —
 * apps/loans/services.py::record_disbursement() is authoritative; this
 * form only shapes the request. */
export function DisbursementForm({ loan }: { loan: AdminLoanDetail }) {
  const disburseLoan = useDisburseLoan(loan.id);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<DisbursementFormValues>({
    resolver: zodResolver(disbursementSchema),
    defaultValues: { amount: loan.principal, method: "MOBILE_MONEY" },
  });

  const onSubmit = async (values: DisbursementFormValues) => {
    setSubmitError(null);
    try {
      await disburseLoan.mutateAsync({
        amount: values.amount,
        method: values.method,
        external_transaction_reference: values.external_transaction_reference,
        notes: values.notes,
        evidence_file: evidenceFile,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setSubmitError(extractErrorDetail(error.body) ?? "This loan can't be disbursed right now.");
        return;
      }
      setSubmitError("Couldn't record this disbursement. Please try again.");
    }
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="grid max-w-lg grid-cols-1 gap-4 sm:grid-cols-2"
    >
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="amount">Amount (GHS)</Label>
        <Input id="amount" inputMode="decimal" {...register("amount")} />
        {errors.amount && <p className="text-destructive text-sm">{errors.amount.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="method">Method</Label>
        <Select id="method" {...register("method")}>
          <option value="MOBILE_MONEY">Mobile Money</option>
          <option value="BANK">Bank</option>
        </Select>
      </div>
      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <Label htmlFor="external_transaction_reference">
          External transaction reference (optional)
        </Label>
        <Input
          id="external_transaction_reference"
          {...register("external_transaction_reference")}
        />
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
      {submitError && <p className="text-destructive text-sm sm:col-span-2">{submitError}</p>}
      <div className="sm:col-span-2">
        <Button type="submit" disabled={isSubmitting || disburseLoan.isPending}>
          {disburseLoan.isPending ? "Recording…" : "Record disbursement"}
        </Button>
      </div>
    </form>
  );
}
