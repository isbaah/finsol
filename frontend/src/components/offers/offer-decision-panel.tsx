"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import {
  SignatureCanvas,
  type SignatureCanvasHandle,
} from "@/components/agreements/signature-canvas";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  useAcceptOffer,
  useRejectOffer,
  useRequestOfferRevision,
} from "@/features/agreements/use-agreements";
import type { CustomerOffer } from "@/features/offers/types";
import { ApiError } from "@/lib/api-client";
import { formatGHS } from "@/lib/format";
import {
  agreementAcceptanceSchema,
  type AgreementAcceptanceFormValues,
} from "@/schemas/agreement-acceptance";

/** Displayed copy only — the authoritative acceptance text lives (and is
 * versioned) server-side in apps/agreements/services.py::_acceptance_text().
 * Keep the wording and "v1" tag here in sync with that function; a real
 * wording change on the backend bumps ACCEPTANCE_TEXT_VERSION and this
 * copy should be updated to match in the same change. */
const ACCEPTANCE_TEXT_V1 =
  "I confirm that I have reviewed the full offer summary above, including the principal, " +
  "interest, total repayable amount, and repayment schedule. I agree to repay this loan " +
  "according to these terms and authorise the lender to proceed.";

function extractErrorDetail(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return null;
}

type Mode = "idle" | "accept" | "reject" | "revision";

/** Stage 8's "signature experience" (master prompt Section 15): checkbox +
 * versioned acceptance text, typed legal name, drawn signature, and a final
 * confirmation dialog before the offer is actually accepted. Reject/
 * request-revision are simpler single-reason forms next to it, all driven
 * by the same offer. */
export function OfferDecisionPanel({ offer }: { offer: CustomerOffer }) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("idle");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [signatureError, setSignatureError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [pendingPayload, setPendingPayload] = useState<{
    typed_legal_name: string;
    signature_image: string;
  } | null>(null);
  const signatureRef = useRef<SignatureCanvasHandle>(null);

  const acceptOffer = useAcceptOffer(offer.id);
  const rejectOffer = useRejectOffer(offer.id);
  const requestRevision = useRequestOfferRevision(offer.id);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<AgreementAcceptanceFormValues>({
    resolver: zodResolver(agreementAcceptanceSchema),
    defaultValues: { typed_legal_name: "", declaration_accepted: false },
  });

  if (offer.status !== "SENT") return null;

  // The signature lives in an imperative canvas ref, not RHF field state
  // (it's drawn, not typed), so this callback has to read `.current` itself
  // once RHF's own field validation has passed — it's only ever invoked
  // from the form's real submit event (see `openConfirmDialog` below), never
  // during render, but the react-hooks/refs rule can't see through
  // react-hook-form's handleSubmit() far enough to prove that statically.
  // eslint-disable-next-line react-hooks/refs
  const openConfirmDialog = handleSubmit((values) => {
    setSignatureError(null);
    const signature = signatureRef.current?.toDataURL();
    if (!signature) {
      setSignatureError("Draw your signature before continuing.");
      return;
    }
    setPendingPayload({ typed_legal_name: values.typed_legal_name, signature_image: signature });
    setConfirmOpen(true);
  });

  const handleConfirmAccept = async () => {
    if (!pendingPayload) return;
    setSubmitError(null);
    try {
      const result = await acceptOffer.mutateAsync({
        typed_legal_name: pendingPayload.typed_legal_name,
        declaration_accepted: true,
        signature_image: pendingPayload.signature_image,
      });
      setConfirmOpen(false);
      toast.success("Offer accepted — your agreement has been generated.");
      router.push(`/loans/${result.loan.id}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setSubmitError(extractErrorDetail(error.body) ?? "This offer can no longer be accepted.");
        return;
      }
      setSubmitError("Couldn't accept this offer. Please try again.");
    }
  };

  const handleReject = async () => {
    setSubmitError(null);
    try {
      await rejectOffer.mutateAsync(reason);
      toast.success("Offer declined.");
      router.push(`/requests/${offer.loan_request_id}`);
    } catch {
      setSubmitError("Couldn't decline this offer. Please try again.");
    }
  };

  const handleRequestRevision = async () => {
    if (!reason.trim()) return;
    setSubmitError(null);
    try {
      await requestRevision.mutateAsync(reason);
      toast.success("Revision requested.");
      router.push(`/requests/${offer.loan_request_id}`);
    } catch {
      setSubmitError("Couldn't submit your revision request. Please try again.");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {mode === "idle" && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setMode("accept")}>Accept offer</Button>
          <Button variant="outline" onClick={() => setMode("revision")}>
            Request revision
          </Button>
          <Button variant="destructive" onClick={() => setMode("reject")}>
            Reject offer
          </Button>
        </div>
      )}

      {mode === "accept" && (
        <Card size="sm" className="max-w-xl">
          <CardContent className="flex flex-col gap-4">
            <p className="text-foreground text-sm font-semibold">Confirm and sign</p>
            <form onSubmit={openConfirmDialog} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="typed_legal_name">Typed full legal name</Label>
                <Input id="typed_legal_name" {...register("typed_legal_name")} />
                {errors.typed_legal_name && (
                  <p className="text-destructive text-sm">{errors.typed_legal_name.message}</p>
                )}
              </div>
              <Controller<AgreementAcceptanceFormValues, "declaration_accepted">
                control={control}
                name="declaration_accepted"
                render={({ field }) => (
                  <div className="flex items-start gap-2">
                    <Checkbox
                      id="declaration_accepted"
                      checked={field.value ?? false}
                      onCheckedChange={(checked) => field.onChange(checked)}
                    />
                    <Label
                      htmlFor="declaration_accepted"
                      className="text-muted-foreground text-sm font-normal"
                    >
                      {ACCEPTANCE_TEXT_V1} (acceptance text version v1)
                    </Label>
                  </div>
                )}
              />
              {errors.declaration_accepted && (
                <p className="text-destructive text-sm">{errors.declaration_accepted.message}</p>
              )}
              <div className="flex flex-col gap-1.5">
                <Label>Signature</Label>
                <SignatureCanvas ref={signatureRef} onChange={() => setSignatureError(null)} />
                {signatureError && <p className="text-destructive text-sm">{signatureError}</p>}
              </div>
              <div className="flex gap-2">
                <Button type="submit">Review and accept</Button>
                <Button type="button" variant="outline" onClick={() => setMode("idle")}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {mode === "reject" && (
        <Card size="sm" className="max-w-md">
          <CardContent className="flex flex-col gap-2">
            <Label htmlFor="reject_reason">Reason (optional)</Label>
            <Textarea
              id="reject_reason"
              rows={2}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <div className="flex gap-2">
              <Button variant="destructive" onClick={handleReject} disabled={rejectOffer.isPending}>
                {rejectOffer.isPending ? "Declining…" : "Confirm decline"}
              </Button>
              <Button variant="outline" onClick={() => setMode("idle")}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {mode === "revision" && (
        <Card size="sm" className="max-w-md">
          <CardContent className="flex flex-col gap-2">
            <Label htmlFor="revision_reason">What would you like changed?</Label>
            <Textarea
              id="revision_reason"
              rows={2}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <div className="flex gap-2">
              <Button
                onClick={handleRequestRevision}
                disabled={requestRevision.isPending || !reason.trim()}
              >
                {requestRevision.isPending ? "Submitting…" : "Request revision"}
              </Button>
              <Button variant="outline" onClick={() => setMode("idle")}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {submitError && <p className="text-destructive text-sm">{submitError}</p>}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogTitle>Confirm loan acceptance</DialogTitle>
          <DialogDescription>
            You&apos;re about to accept {formatGHS(offer.total_repayable)} total repayable over{" "}
            {offer.installment_count} installments. This creates a binding, auditable acceptance
            record and cannot be undone.
          </DialogDescription>
          <div className="mt-4 flex justify-end gap-2">
            <DialogClose
              render={
                <Button variant="outline" disabled={acceptOffer.isPending}>
                  Cancel
                </Button>
              }
            />
            <Button onClick={handleConfirmAccept} disabled={acceptOffer.isPending}>
              {acceptOffer.isPending ? "Generating your agreement…" : "Confirm acceptance"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
