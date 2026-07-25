"use client";

import { use, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import type { SMSMessageStatus } from "@/features/messaging/types";
import { useRetrySmsMessage, useSmsMessages, useSmsMessageSummary } from "@/features/messaging/use-messaging";
import { formatDateTime } from "@/lib/format";

const STATUS_OPTIONS: SMSMessageStatus[] = [
  "PENDING",
  "PROCESSING",
  "SENT",
  "DELIVERED",
  "FAILED",
  "CANCELLED",
];

/** Stage 11: "Build SMS history and summary UI" (Section 21: "sent,
 * delivered, failed, and pending counts"). */
export default function SmsActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ loan?: string }>;
}) {
  // Stage 12: the dashboard's upcoming-repayments "SMS history" action
  // links here scoped to one loan.
  const { loan } = use(searchParams);
  const [status, setStatus] = useState<SMSMessageStatus | "">("");
  const { data: summary } = useSmsMessageSummary();
  const { data, isLoading, isError } = useSmsMessages({
    status: status || undefined,
    loan: loan || undefined,
  });
  const retry = useRetrySmsMessage();

  return (
    <main className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">SMS activity</h1>
        <p className="text-muted-foreground text-sm">
          Every message the system has recorded, and its current delivery status.
        </p>
        {loan && (
          <p className="text-muted-foreground mt-1 text-sm">
            Showing messages for one loan.{" "}
            <Link href="/admin/sms-activity" className="text-primary hover:underline">
              Show all messages
            </Link>
          </p>
        )}
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {STATUS_OPTIONS.map((option) => (
            <Card size="sm" key={option}>
              <CardContent>
                <p className="text-muted-foreground text-xs">{option}</p>
                <p className="text-foreground text-lg font-semibold">{summary[option]}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Select
        value={status}
        onChange={(event) => setStatus(event.target.value as SMSMessageStatus | "")}
        className="max-w-56"
      >
        <option value="">All statuses</option>
        {STATUS_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </Select>

      {isLoading && <p className="text-muted-foreground text-sm">Loading messages…</p>}
      {isError && (
        <p className="text-destructive text-sm">Couldn&apos;t load SMS activity. Please try again.</p>
      )}
      {!isLoading && !isError && data?.results.length === 0 && (
        <p className="text-muted-foreground text-sm">No messages match this filter.</p>
      )}

      {!isLoading && !isError && data && data.results.length > 0 && (
        <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border text-muted-foreground border-b text-left">
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Recipient</th>
                <th className="px-5 py-3 font-medium">Customer</th>
                <th className="px-5 py-3 font-medium">Loan</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Attempts</th>
                <th className="px-5 py-3 font-medium">Created</th>
                <th className="px-5 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((message) => (
                <tr key={message.id} className="border-border hover:bg-muted/60 border-b transition-colors last:border-0">
                  <td className="px-5 py-3">{message.message_type}</td>
                  <td className="px-5 py-3">{message.recipient_phone_e164}</td>
                  <td className="px-5 py-3">{message.customer_name}</td>
                  <td className="px-5 py-3">{message.loan_number ?? "—"}</td>
                  <td className="px-5 py-3">
                    <span
                      className={
                        message.status === "FAILED"
                          ? "text-red-700 dark:text-red-400"
                          : message.status === "SENT" || message.status === "DELIVERED"
                            ? "text-emerald-700 dark:text-emerald-400"
                            : "text-muted-foreground"
                      }
                    >
                      {message.status}
                    </span>
                  </td>
                  <td className="px-5 py-3">{message.attempt_count}</td>
                  <td className="px-5 py-3">{formatDateTime(message.created_at)}</td>
                  <td className="px-5 py-3">
                    {message.status === "FAILED" && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={retry.isPending}
                        onClick={() => retry.mutate(message.id)}
                      >
                        Retry
                      </Button>
                    )}
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
