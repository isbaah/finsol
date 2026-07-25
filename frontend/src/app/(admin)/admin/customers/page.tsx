"use client";

import { useCustomers } from "@/features/customers/use-customers";

const DISBURSEMENT_METHOD_LABEL: Record<string, string> = {
  MOBILE_MONEY: "Mobile Money",
  BANK: "Bank",
};

export default function AdminCustomersPage() {
  const { data, isLoading, isError } = useCustomers();

  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Customers</h1>
        <p className="text-muted-foreground text-sm">
          Payout account numbers are masked here — full details are only ever shown through the
          disbursement workflow (Stage 9).
        </p>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Loading customers…</p>}
      {isError && (
        <p className="text-destructive text-sm">Couldn&apos;t load customers. Please try again.</p>
      )}
      {!isLoading && !isError && data?.results.length === 0 && (
        <p className="text-muted-foreground text-sm">No customers have completed onboarding yet.</p>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">Phone</th>
                <th className="px-5 py-3 font-medium">Payout method</th>
                <th className="px-5 py-3 font-medium">Account</th>
                <th className="px-5 py-3 font-medium">Profile completed</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((customer) => (
                <tr key={customer.id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                  <td className="px-5 py-3">{customer.full_name || "—"}</td>
                  <td className="px-5 py-3">{customer.email}</td>
                  <td className="px-5 py-3">{customer.phone_number_e164}</td>
                  <td className="px-5 py-3">
                    {DISBURSEMENT_METHOD_LABEL[customer.preferred_disbursement_method]}
                  </td>
                  <td className="px-5 py-3">
                    {customer.preferred_disbursement_method === "MOBILE_MONEY"
                      ? customer.mobile_money_number
                      : customer.bank_account_number}
                  </td>
                  <td className="px-5 py-3">
                    {customer.profile_completed_at
                      ? new Date(customer.profile_completed_at).toLocaleDateString()
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
