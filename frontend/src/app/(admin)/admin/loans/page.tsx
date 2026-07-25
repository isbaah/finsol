"use client";

import { use, useState } from "react";
import Link from "next/link";

import { LoanStatusBadge } from "@/components/loans/loan-status-badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { LOAN_STATUS_LABEL } from "@/features/loans/status";
import type { LoanStatus } from "@/features/loans/types";
import { useAdminLoans } from "@/features/loans/use-loans";
import { formatGHS } from "@/lib/format";

export default function AdminLoansPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status: initialStatus } = use(searchParams);
  const [status, setStatus] = useState<LoanStatus | "">(
    (initialStatus as LoanStatus | undefined) ?? "",
  );
  const [search, setSearch] = useState("");
  const { data, isLoading, isError } = useAdminLoans({
    status: status || undefined,
    search: search || undefined,
  });

  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Loans</h1>
        <p className="text-muted-foreground text-sm">
          Approve accepted loans and record manual disbursements.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search by loan number or customer"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w-xs"
        />
        <Select
          value={status}
          onChange={(event) => setStatus(event.target.value as LoanStatus | "")}
          className="max-w-56"
        >
          <option value="">All statuses</option>
          {Object.entries(LOAN_STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Loading loans…</p>}
      {isError && (
        <p className="text-destructive text-sm">Couldn&apos;t load loans. Please try again.</p>
      )}
      {!isLoading && !isError && data?.results.length === 0 && (
        <p className="text-muted-foreground text-sm">No loans match these filters.</p>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Loan number</th>
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Principal</th>
                <th className="px-5 py-3 font-medium">Outstanding</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((loan) => (
                <tr key={loan.id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                  <td className="px-5 py-3">{loan.loan_number}</td>
                  <td className="px-5 py-3">{loan.customer_name || loan.customer_email}</td>
                  <td className="px-5 py-3">{formatGHS(loan.principal)}</td>
                  <td className="px-5 py-3">{formatGHS(loan.outstanding_balance)}</td>
                  <td className="px-5 py-3">
                    <LoanStatusBadge status={loan.status} />
                  </td>
                  <td className="px-5 py-3">
                    <Link href={`/admin/loans/${loan.id}`} className="text-primary hover:underline">
                      View
                    </Link>
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
