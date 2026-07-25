import { BackButton } from "@/components/shared/back-button";
import { LoanRequestForm } from "@/components/requests/loan-request-form";

export default function NewLoanRequestPage() {
  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <BackButton fallbackHref="/dashboard" label="Dashboard" />
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Request a loan</h1>
        <p className="text-muted-foreground text-sm">
          Tell us how much you need and what it&apos;s for — our team reviews every request and
          sends back an offer with the actual terms.
        </p>
      </div>
      <LoanRequestForm />
    </main>
  );
}
