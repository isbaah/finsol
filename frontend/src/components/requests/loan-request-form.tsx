"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "@/lib/api-client";
import { applyDrfErrors } from "@/lib/drf-errors";
import { useMyProfile } from "@/features/profile/use-profile";
import { useCreateLoanRequest } from "@/features/loan-requests/use-loan-requests";
import { type LoanRequestFormValues, loanRequestSchema } from "@/schemas/loan-request";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const PAYOUT_METHOD_LABEL: Record<string, string> = {
  MOBILE_MONEY: "Mobile Money",
  BANK: "Bank",
};

export function LoanRequestForm() {
  const router = useRouter();
  const { data: profile } = useMyProfile();
  const createLoanRequest = useCreateLoanRequest();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoanRequestFormValues>({
    resolver: zodResolver(loanRequestSchema),
    defaultValues: {
      requested_amount: "",
      purpose: "",
      requested_term_unit: "MONTH",
      customer_notes: "",
      declaration: false,
    },
  });

  const onSubmit = async (values: LoanRequestFormValues) => {
    setSubmitError(null);
    try {
      const loanRequest = await createLoanRequest.mutateAsync({
        requested_amount: values.requested_amount,
        purpose: values.purpose,
        requested_term_count: values.requested_term_count,
        requested_term_unit: values.requested_term_unit || undefined,
        customer_notes: values.customer_notes,
      });
      router.push(`/requests/${loanRequest.id}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        applyDrfErrors(error, setError, "requested_amount");
        return;
      }
      if (error instanceof ApiError && error.status === 403) {
        setSubmitError(
          "Your account isn't eligible to request a loan yet — verify your email and complete your profile first.",
        );
        return;
      }
      setSubmitError("Something went wrong submitting your request. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex w-full max-w-md flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="requested_amount">Requested amount (GHS)</Label>
        <Input id="requested_amount" inputMode="decimal" {...register("requested_amount")} />
        {errors.requested_amount && (
          <p className="text-destructive text-sm">{errors.requested_amount.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="purpose">Loan purpose</Label>
        <Textarea id="purpose" rows={3} {...register("purpose")} />
        {errors.purpose && <p className="text-destructive text-sm">{errors.purpose.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="requested_term_count">Preferred term count</Label>
          <Input
            id="requested_term_count"
            type="number"
            {...register("requested_term_count", {
              setValueAs: (value) => (value === "" ? undefined : Number(value)),
            })}
          />
          {errors.requested_term_count && (
            <p className="text-destructive text-sm">{errors.requested_term_count.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="requested_term_unit">Term unit</Label>
          <Select id="requested_term_unit" {...register("requested_term_unit")}>
            <option value="MONTH">Month</option>
            <option value="WEEK">Week</option>
          </Select>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="customer_notes">Anything else we should know? (optional)</Label>
        <Textarea id="customer_notes" rows={2} {...register("customer_notes")} />
      </div>

      {profile && (
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Payout method on file</p>
            <p className="text-foreground text-sm font-medium">
              {PAYOUT_METHOD_LABEL[profile.preferred_disbursement_method]}
              {" — "}
              {profile.preferred_disbursement_method === "MOBILE_MONEY"
                ? profile.mobile_money_number
                : profile.bank_account_number}
            </p>
            <p className="text-muted-foreground mt-1 text-xs">
              Funds are sent to this destination if your request is approved. Change it on your{" "}
              <a href="/profile" className="underline">
                profile page
              </a>{" "}
              before submitting if it&apos;s wrong.
            </p>
          </CardContent>
        </Card>
      )}

      <p className="text-muted-foreground text-sm">
        The administrator reviews every request and determines the final loan terms — the amount,
        rate, and schedule you receive may differ from what you request here.
      </p>

      <Controller<LoanRequestFormValues, "declaration">
        control={control}
        name="declaration"
        render={({ field }) => (
          <div className="flex items-start gap-2">
            <Checkbox
              id="declaration"
              checked={field.value ?? false}
              onCheckedChange={(checked) => field.onChange(checked)}
            />
            <Label htmlFor="declaration" className="text-muted-foreground text-sm font-normal">
              The information I&apos;ve provided is accurate.
            </Label>
          </div>
        )}
      />
      {errors.declaration && (
        <p className="text-destructive text-sm">{errors.declaration.message}</p>
      )}

      {submitError && <p className="text-destructive text-sm">{submitError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Submitting…" : "Submit request"}
      </Button>
    </form>
  );
}
