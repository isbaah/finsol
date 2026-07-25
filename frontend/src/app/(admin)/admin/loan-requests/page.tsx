"use client";

import { useState } from "react";
import Link from "next/link";

import { StatusBadge } from "@/components/requests/status-badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { LOAN_REQUEST_STATUS_LABEL } from "@/features/loan-requests/status";
import { useAdminLoanRequests } from "@/features/loan-requests/use-admin-loan-requests";
import type { LoanRequestStatus } from "@/features/loan-requests/types";
import { formatDateTime, formatGHS } from "@/lib/format";

export default function AdminLoanRequestsPage() {
  const [status, setStatus] = useState<LoanRequestStatus | "">("");
  const [search, setSearch] = useState("");
  const { data, isLoading, isError } = useAdminLoanRequests({
    status: status || undefined,
    search: search || undefined,
  });

  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Loan requests</h1>
        <p className="text-muted-foreground text-sm">
          Review, assign, and respond to customer requests.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search by request number or customer"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w-xs"
        />
        <Select
          value={status}
          onChange={(event) => setStatus(event.target.value as LoanRequestStatus | "")}
          className="max-w-48"
        >
          <option value="">All statuses</option>
          {Object.entries(LOAN_REQUEST_STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Loading requests…</p>}
      {isError && (
        <p className="text-destructive text-sm">Couldn&apos;t load the queue. Please try again.</p>
      )}
      {!isLoading && !isError && data?.results.length === 0 && (
        <p className="text-muted-foreground text-sm">No requests match these filters.</p>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Request number</th>
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Requested amount</th>
                <th className="px-5 py-3 font-medium">Submitted</th>
                <th className="px-5 py-3 font-medium">Purpose</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Assigned officer</th>
                <th className="px-5 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((request) => (
                <tr key={request.id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                  <td className="px-5 py-3">{request.request_number}</td>
                  <td className="px-5 py-3">{request.customer_name || request.customer_email}</td>
                  <td className="px-5 py-3">{formatGHS(request.requested_amount)}</td>
                  <td className="px-5 py-3">
                    {request.submitted_at ? formatDateTime(request.submitted_at) : "—"}
                  </td>
                  <td className="px-5 py-3">{request.purpose}</td>
                  <td className="px-5 py-3">
                    <StatusBadge status={request.status} />
                  </td>
                  <td className="px-5 py-3">{request.assigned_to_name || "—"}</td>
                  <td className="px-5 py-3">
                    <Link
                      href={`/admin/loan-requests/${request.id}`}
                      className="text-primary hover:underline"
                    >
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
