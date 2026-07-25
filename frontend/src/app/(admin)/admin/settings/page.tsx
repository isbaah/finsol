"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  useAdminRepaymentAccount,
  useUpdateRepaymentAccount,
} from "@/features/repayments/use-repayments";
import type { RepaymentAccount, RepaymentAccountPayload } from "@/features/repayments/types";
import { ApiError } from "@/lib/api-client";

/** Super-admin settings: the company collection account shown to customers
 * (with copy actions) whenever they open an installment's payment details.
 * Any staff role can view; only the SUPER_ADMIN can save. */
export default function AdminSettingsPage() {
  const { data, isLoading, isError } = useAdminRepaymentAccount();

  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground text-sm">
          Company-level configuration. More settings arrive with later stages.
        </p>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Repayment collection account</CardTitle>
          <CardDescription>
            Shown to customers (with copy buttons) when they open an installment&apos;s payment
            details — this is where they send repayments. Super admin only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && <Skeleton className="h-40 w-full" />}
          {isError && (
            <p className="text-destructive text-sm">Couldn&apos;t load the current details.</p>
          )}
          {/* Keyed on updated_at so a fresh server copy re-seeds the form
              without needing a sync-state effect. */}
          {!isLoading && !isError && data && (
            <RepaymentAccountForm key={data.updated_at} initial={data} />
          )}
        </CardContent>
      </Card>
    </main>
  );
}

function RepaymentAccountForm({ initial }: { initial: RepaymentAccount }) {
  const update = useUpdateRepaymentAccount();
  const [values, setValues] = useState<RepaymentAccountPayload>({
    mobile_money_network: initial.mobile_money_network,
    mobile_money_number: initial.mobile_money_number,
    mobile_money_account_name: initial.mobile_money_account_name,
    bank_name: initial.bank_name,
    bank_account_name: initial.bank_account_name,
    bank_account_number: initial.bank_account_number,
    payment_instructions: initial.payment_instructions,
  });
  const [error, setError] = useState<string | null>(null);

  const set = (field: keyof RepaymentAccountPayload) => (value: string) =>
    setValues((current) => ({ ...current, [field]: value }));

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await update.mutateAsync(values);
      toast.success("Repayment account saved.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Only the super admin can change the repayment account.");
        return;
      }
      setError("Couldn't save the repayment account. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <p className="text-foreground text-sm font-semibold">Mobile money</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="mm-network">Network</Label>
          <Select
            id="mm-network"
            value={values.mobile_money_network}
            onChange={(event) => set("mobile_money_network")(event.target.value)}
          >
            <option value="">Not set</option>
            <option value="MTN">MTN</option>
            <option value="TELECEL">Telecel</option>
            <option value="AIRTELTIGO">AirtelTigo</option>
            <option value="OTHER">Other</option>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="mm-number">Number</Label>
          <Input
            id="mm-number"
            value={values.mobile_money_number}
            onChange={(event) => set("mobile_money_number")(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="mm-name">Account name</Label>
          <Input
            id="mm-name"
            value={values.mobile_money_account_name}
            onChange={(event) => set("mobile_money_account_name")(event.target.value)}
          />
        </div>
      </div>

      <p className="text-foreground text-sm font-semibold">Bank</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="bank-name">Bank name</Label>
          <Input
            id="bank-name"
            value={values.bank_name}
            onChange={(event) => set("bank_name")(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="bank-account-name">Account name</Label>
          <Input
            id="bank-account-name"
            value={values.bank_account_name}
            onChange={(event) => set("bank_account_name")(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="bank-account-number">Account number</Label>
          <Input
            id="bank-account-number"
            value={values.bank_account_number}
            onChange={(event) => set("bank_account_number")(event.target.value)}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="instructions">Payment instructions (optional)</Label>
        <Textarea
          id="instructions"
          rows={2}
          placeholder="e.g. Use your loan number as the payment reference."
          value={values.payment_instructions}
          onChange={(event) => set("payment_instructions")(event.target.value)}
        />
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}
      <Button type="submit" disabled={update.isPending} className="self-start">
        {update.isPending ? "Saving…" : "Save repayment account"}
      </Button>
    </form>
  );
}
