import { apiFetch } from "@/lib/api-client";

import type {
  ChartMonths,
  CollectionsChartRow,
  DashboardMetrics,
  OverdueSummary,
  RecentTransactionRow,
  UpcomingRepaymentRow,
} from "./types";

export function getDashboardMetrics() {
  return apiFetch<DashboardMetrics>("/api/v1/admin/dashboard/metrics/");
}

export function getCollectionsChart(months: ChartMonths) {
  return apiFetch<CollectionsChartRow[]>(
    `/api/v1/admin/dashboard/collections-chart/?months=${months}`,
  );
}

export function getUpcomingRepayments() {
  return apiFetch<UpcomingRepaymentRow[]>("/api/v1/admin/dashboard/upcoming-repayments/");
}

export function getOverdueSummary() {
  return apiFetch<OverdueSummary>("/api/v1/admin/dashboard/overdue-summary/");
}

export function getRecentTransactions() {
  return apiFetch<RecentTransactionRow[]>("/api/v1/admin/dashboard/recent-transactions/");
}
