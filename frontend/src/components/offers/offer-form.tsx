"use client";

import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api-client";
import { applyDrfErrors } from "@/lib/drf-errors";
import { sendOffer as sendOfferRequest } from "@/features/offers/api";
import { useAdminOffer, useCreateOffer, useUpdateDraftOffer } from "@/features/offers/use-offers";
import { ADMIN_LOAN_REQUESTS_QUERY_KEY } from "@/features/loan-requests/use-admin-loan-requests";
import type { AdminOfferDetail } from "@/features/offers/types";
import { formatDate, formatGHS } from "@/lib/format";
import { type OfferFormValues, offerSchema } from "@/schemas/offer";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

function toFormValues(offer: AdminOfferDetail): OfferFormValues {
  return {
    principal: offer.principal,
    interest_rate_percent: offer.interest_rate_percent,
    term_count: offer.term_count,
    term_unit: offer.term_unit,
    first_due_date: offer.first_due_date,
    offer_expiry_date: offer.offer_expiry_date ?? "",
    customer_terms: offer.customer_terms,
    internal_notes: offer.internal_notes,
  };
}

/** Stage 7's offer form: create a new DRAFT version for a request, or edit
 * an existing one while it's still DRAFT. `offerId` selects edit mode;
 * omit it to create the request's next version. Reuses the exact same
 * calculate() pipeline as the Stage 5 preview form — see
 * apps/loan_offers/views.py's _run_calculation(). */
export function OfferForm({ loanRequestId, offerId }: { loanRequestId: string; offerId?: string }) {
  const existing = useAdminOffer(offerId ?? "");
  const createOffer = useCreateOffer(loanRequestId);
  const updateOffer = useUpdateDraftOffer(offerId ?? "");
  const queryClient = useQueryClient();
  // Not useSendOffer(offerId): in create mode offerId is unknown until the
  // draft is actually created, so the id to send has to be read from
  // `offer.id` at click time, not fixed when this component mounted.
  const sendOfferMutation = useMutation({
    mutationFn: (id: string) => sendOfferRequest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_LOAN_REQUESTS_QUERY_KEY });
    },
  });
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [savedOffer, setSavedOffer] = useState<AdminOfferDetail | null>(null);

  const isEditing = !!offerId;
  const offer = savedOffer ?? existing.data;

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<OfferFormValues>({
    resolver: zodResolver(offerSchema),
    defaultValues: { term_unit: "MONTH" },
  });

  useEffect(() => {
    if (existing.data) reset(toFormValues(existing.data));
  }, [existing.data, reset]);

  const onSubmit = async (values: OfferFormValues) => {
    setSubmitError(null);
    const payload = {
      principal: values.principal,
      interest_rate_percent: values.interest_rate_percent,
      term_count: values.term_count,
      term_unit: values.term_unit,
      first_due_date: values.first_due_date,
      offer_expiry_date: values.offer_expiry_date || undefined,
      customer_terms: values.customer_terms,
      internal_notes: values.internal_notes,
    };
    try {
      const result = isEditing
        ? await updateOffer.mutateAsync(payload)
        : await createOffer.mutateAsync(payload);
      setSavedOffer(result);
      toast.success(isEditing ? "Draft updated." : "Draft offer created.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        applyDrfErrors(error, setError, "principal");
        return;
      }
      if (error instanceof ApiError && error.status === 409) {
        setSubmitError("This request isn't open for a new offer right now.");
        return;
      }
      setSubmitError("Couldn't save this offer. Check the values and try again.");
    }
  };

  const handleSend = async () => {
    if (!offer) return;
    setSubmitError(null);
    try {
      const sent = await sendOfferMutation.mutateAsync(offer.id);
      setSavedOffer(sent);
      toast.success("Offer sent to the customer.");
    } catch {
      setSubmitError("Couldn't send this offer. Please try again.");
    }
  };

  return (
    <div className="flex flex-col gap-4">
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
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="first_due_date">First due date</Label>
          <Input id="first_due_date" type="date" {...register("first_due_date")} />
          {errors.first_due_date && (
            <p className="text-destructive text-sm">{errors.first_due_date.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="offer_expiry_date">Offer expires (optional)</Label>
          <Input id="offer_expiry_date" type="date" {...register("offer_expiry_date")} />
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="customer_terms">Customer-facing terms</Label>
          <Textarea id="customer_terms" rows={2} {...register("customer_terms")} />
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="internal_notes">Internal notes (never shown to the customer)</Label>
          <Textarea id="internal_notes" rows={2} {...register("internal_notes")} />
        </div>
        <div className="flex items-end gap-2">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : isEditing ? "Save draft" : "Create draft offer"}
          </Button>
        </div>
      </form>

      {submitError && <p className="text-destructive text-sm">{submitError}</p>}

      {offer && (
        <Card size="sm" className="max-w-md">
          <CardContent className="flex flex-col gap-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Version</span>
              <span className="text-foreground text-sm font-medium">{offer.version_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Total repayable</span>
              <span className="text-foreground text-sm font-medium">
                {formatGHS(offer.total_repayable)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">First due date</span>
              <span className="text-foreground text-sm font-medium">
                {formatDate(offer.first_due_date)}
              </span>
            </div>
            {offer.status === "DRAFT" && (
              <Button onClick={handleSend} disabled={sendOfferMutation.isPending}>
                {sendOfferMutation.isPending ? "Sending…" : "Send offer to customer"}
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
