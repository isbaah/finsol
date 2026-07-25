"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useAmortizationPreview } from "@/features/amortization/use-amortization-preview";
import type { AmortizationPreviewResponse } from "@/features/amortization/types";
import { formatDate, formatGHS } from "@/lib/format";
import {
  type AmortizationPreviewFormValues,
  amortizationPreviewSchema,
} from "@/schemas/amortization";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

export function AmortizationPreviewForm() {
  const preview = useAmortizationPreview();
  const [result, setResult] = useState<AmortizationPreviewResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AmortizationPreviewFormValues>({
    resolver: zodResolver(amortizationPreviewSchema),
    defaultValues: { term_unit: "MONTH" },
  });

  const onSubmit = async (values: AmortizationPreviewFormValues) => {
    setSubmitError(null);
    setResult(null);
    try {
      const response = await preview.mutateAsync({
        principal: values.principal,
        interest_rate_percent: values.interest_rate_percent,
        term_count: values.term_count,
        term_unit: values.term_unit,
        first_due_date: values.first_due_date,
      });
      setResult(response);
    } catch {
      setSubmitError(
        "Couldn't calculate a schedule for these terms. Check the values and try again.",
      );
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2"
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="principal">Principal (GHS)</Label>
          <Input id="principal" inputMode="decimal" {...register("principal")} />
          {errors.principal && (
            <p className="text-destructive text-sm">{errors.principal.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="interest_rate_percent">Total-term interest rate (%)</Label>
          <Input
            id="interest_rate_percent"
            inputMode="decimal"
            {...register("interest_rate_percent")}
          />
          {errors.interest_rate_percent && (
            <p className="text-destructive text-sm">{errors.interest_rate_percent.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="term_count">Term count</Label>
          <Input
            id="term_count"
            type="number"
            {...register("term_count", { valueAsNumber: true })}
          />
          {errors.term_count && (
            <p className="text-destructive text-sm">{errors.term_count.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="term_unit">Term unit</Label>
          <Select id="term_unit" {...register("term_unit")}>
            <option value="MONTH">Month</option>
            <option value="WEEK">Week</option>
          </Select>
          {errors.term_unit && (
            <p className="text-destructive text-sm">{errors.term_unit.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="first_due_date">First due date</Label>
          <Input id="first_due_date" type="date" {...register("first_due_date")} />
          {errors.first_due_date && (
            <p className="text-destructive text-sm">{errors.first_due_date.message}</p>
          )}
        </div>
        <div className="flex items-end">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Calculating…" : "Calculate schedule"}
          </Button>
        </div>
      </form>

      {submitError && <p className="text-destructive text-sm">{submitError}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Card size="sm">
              <CardContent>
                <p className="text-muted-foreground text-xs">Total interest</p>
                <p className="text-foreground text-lg font-semibold">
                  {formatGHS(result.total_interest)}
                </p>
              </CardContent>
            </Card>
            <Card size="sm">
              <CardContent>
                <p className="text-muted-foreground text-xs">Total repayable</p>
                <p className="text-foreground text-lg font-semibold">
                  {formatGHS(result.total_repayable)}
                </p>
              </CardContent>
            </Card>
            <Card size="sm">
              <CardContent>
                <p className="text-muted-foreground text-xs">Installments</p>
                <p className="text-foreground text-lg font-semibold">{result.installment_count}</p>
              </CardContent>
            </Card>
          </div>

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
                {result.installments.map((installment) => (
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
        </div>
      )}
    </div>
  );
}
