import { AmortizationPreviewForm } from "@/components/offers/amortization-preview-form";

export default function OfferAmortizationPreviewPage() {
  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">
          Amortization preview
        </h1>
        <p className="text-muted-foreground text-sm">
          Flat total-term interest only. Nothing here is saved — this is a preview of what an
          offer&apos;s schedule would look like before it&apos;s created (Stage 7).
        </p>
      </div>
      <AmortizationPreviewForm />
    </main>
  );
}
