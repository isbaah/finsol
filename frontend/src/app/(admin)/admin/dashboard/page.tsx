"use client";

import Link from "next/link";

import { CollectionsChart } from "@/components/dashboard/collections-chart";
import { MetricCards } from "@/components/dashboard/metric-cards";
import { NewRequestsTable } from "@/components/dashboard/new-requests-table";
import { OverdueSummaryTable } from "@/components/dashboard/overdue-summary-table";
import { RecentTransactionsPanel } from "@/components/dashboard/recent-activity-panels";
import { UpcomingRepaymentsTable } from "@/components/dashboard/upcoming-repayments-table";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboardMetrics } from "@/features/dashboards/use-dashboards";

/** Stage 12: the Section 16 CRM-style dashboard. All figures come from
 * apps/dashboards — nothing is computed client-side. */
export default function AdminDashboardPage() {
  const { data: metrics, isLoading, isError } = useDashboardMetrics();

  const queues = [
    {
      label: "New loan requests",
      count: metrics?.new_request_count,
      href: "/admin/loan-requests",
    },
    {
      label: "Awaiting approval",
      count: metrics?.pending_approval_count,
      href: "/admin/loans?status=PENDING_APPROVAL",
    },
    {
      label: "Awaiting disbursement",
      count: metrics?.awaiting_disbursement_count,
      href: "/admin/loans?status=APPROVED_FOR_DISBURSEMENT",
    },
    {
      label: "Payment claims",
      count: metrics?.pending_payment_claim_count,
      href: "/admin/payment-claims",
    },
  ];

  return (
    <main className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          Portfolio health, collections, and today&apos;s work queues.
        </p>
      </div>

      <MetricCards metrics={metrics} isLoading={isLoading} isError={isError} />

      <div className="grid grid-cols-1 items-stretch gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {queues.map((queue) => (
          <Card size="sm" key={queue.label} className="h-full">
            <CardContent className="flex h-full items-center justify-between gap-4">
              <div>
                <p className="text-muted-foreground text-xs">{queue.label}</p>
                {isLoading ? (
                  <Skeleton className="mt-1 h-6 w-10" />
                ) : (
                  <p className="text-foreground text-2xl font-semibold">{queue.count ?? 0}</p>
                )}
              </div>
              <Link href={queue.href} className="text-primary text-sm hover:underline">
                Review
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Chart and recent-transactions stretch to the same row height. */}
      <div className="grid grid-cols-1 items-stretch gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <CollectionsChart />
        </div>
        <RecentTransactionsPanel />
      </div>

      <UpcomingRepaymentsTable />
      <OverdueSummaryTable />
      <NewRequestsTable />
    </main>
  );
}
