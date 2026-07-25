"use client";

import Link from "next/link";

import { BackButton } from "@/components/shared/back-button";
import { StatusBadge } from "@/components/requests/status-badge";
import { Button } from "@/components/ui/button";
import { useLoanRequests } from "@/features/loan-requests/use-loan-requests";
import { formatDateTime, formatGHS } from "@/lib/format";

export default function LoanRequestsPage() {
  const { data, isLoading, isError } = useLoanRequests();

  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <BackButton fallbackHref="/dashboard" label="Dashboard" />
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-foreground text-2xl font-semibold tracking-tight">
            Your loan requests
          </h1>
          <p className="text-muted-foreground text-sm">
            Track every request you&apos;ve submitted.
          </p>
        </div>
        <Button nativeButton={false} render={<Link href="/requests/new">Request a loan</Link>} />
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Loading requests…</p>}
      {isError && (
        <p className="text-destructive text-sm">
          Couldn&apos;t load your requests. Please try again.
        </p>
      )}
      {!isLoading && !isError && data?.results.length === 0 && (
        <p className="text-muted-foreground text-sm">
          You haven&apos;t submitted a loan request yet.
        </p>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Request number</th>
                <th className="px-5 py-3 font-medium">Amount</th>
                <th className="px-5 py-3 font-medium">Purpose</th>
                <th className="px-5 py-3 font-medium">Submitted</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((request) => (
                <tr key={request.id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                  <td className="px-5 py-3">
                    <Link href={`/requests/${request.id}`} className="text-primary hover:underline">
                      {request.request_number}
                    </Link>
                  </td>
                  <td className="px-5 py-3">{formatGHS(request.requested_amount)}</td>
                  <td className="px-5 py-3">{request.purpose}</td>
                  <td className="px-5 py-3">
                    {request.submitted_at ? formatDateTime(request.submitted_at) : "—"}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={request.status} />
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
