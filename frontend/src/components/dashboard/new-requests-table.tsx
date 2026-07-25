"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/requests/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminLoanRequests } from "@/features/loan-requests/use-admin-loan-requests";
import { formatDateTime, formatGHS } from "@/lib/format";

/** Section 16's new-loan-requests table — the SUBMITTED queue, compact,
 * with a link into the full review page. */
export function NewRequestsTable() {
  const { data, isLoading, isError } = useAdminLoanRequests({ status: "SUBMITTED" });

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h2 className="text-foreground text-base font-semibold tracking-tight">New loan requests</h2>
        <Link href="/admin/loan-requests" className="text-primary text-sm hover:underline">
          View all requests
        </Link>
      </div>

      {isLoading && <Skeleton className="h-24 w-full" />}
      {isError && (
        <p className="text-destructive text-sm">
          Couldn&apos;t load new requests. Please try again.
        </p>
      )}
      {!isLoading && !isError && data?.results.length === 0 && (
        <p className="text-muted-foreground text-sm">No new requests are waiting for review.</p>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Request</th>
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Amount</th>
                <th className="px-5 py-3 font-medium">Submitted</th>
                <th className="px-5 py-3 font-medium">Purpose</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Assigned</th>
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
                  <td className="max-w-48 truncate px-4 py-2">{request.purpose}</td>
                  <td className="px-5 py-3">
                    <StatusBadge status={request.status} />
                  </td>
                  <td className="px-5 py-3">{request.assigned_to_name || "—"}</td>
                  <td className="px-5 py-3">
                    <Link
                      href={`/admin/loan-requests/${request.id}`}
                      className="text-primary hover:underline"
                    >
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
