"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getCollectionsChart,
  getDashboardMetrics,
  getOverdueSummary,
  getRecentTransactions,
  getUpcomingRepayments,
} from "./api";
import type { ChartMonths } from "./types";

export function useDashboardMetrics() {
  return useQuery({ queryKey: ["dashboard-metrics"], queryFn: getDashboardMetrics });
}

export function useCollectionsChart(months: ChartMonths) {
  return useQuery({
    queryKey: ["dashboard-collections-chart", months],
    queryFn: () => getCollectionsChart(months),
  });
}

export function useUpcomingRepayments() {
  return useQuery({
    queryKey: ["dashboard-upcoming-repayments"],
    queryFn: getUpcomingRepayments,
  });
}

export function useOverdueSummary() {
  return useQuery({ queryKey: ["dashboard-overdue-summary"], queryFn: getOverdueSummary });
}

export function useRecentTransactions() {
  return useQuery({
    queryKey: ["dashboard-recent-transactions"],
    queryFn: getRecentTransactions,
  });
}
