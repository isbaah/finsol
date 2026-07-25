"use client";

import {
  AlertTriangleIcon,
  BanknoteIcon,
  CalendarClockIcon,
  LandmarkIcon,
  WalletIcon,
} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { DashboardMetrics } from "@/features/dashboards/types";
import { formatGHS } from "@/lib/format";

/** Section 16's top metric cards. Definitions live in
 * apps/dashboards/services.py — this component only formats. */
const METRICS = [
  {
    key: "outstanding_portfolio_balance",
    label: "Outstanding portfolio",
    icon: WalletIcon,
    money: true,
    tone: "text-foreground",
  },
  {
    key: "amount_due_this_month",
    label: "Due this month",
    icon: CalendarClockIcon,
    money: true,
    tone: "text-foreground",
  },
  {
    key: "amount_collected_this_month",
    label: "Collected this month",
    icon: BanknoteIcon,
    money: true,
    tone: "text-emerald-700 dark:text-emerald-400",
  },
  {
    key: "overdue_amount",
    label: "Overdue amount",
    icon: AlertTriangleIcon,
    money: true,
    tone: "text-red-700 dark:text-red-400",
  },
  {
    key: "active_loans",
    label: "Active loans",
    icon: LandmarkIcon,
    money: false,
    tone: "text-foreground",
  },
] as const;

export function MetricCards({
  metrics,
  isLoading,
  isError,
}: {
  metrics: DashboardMetrics | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isError) {
    return (
      <p className="text-destructive text-sm">
        Couldn&apos;t load portfolio metrics. Please try again.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {METRICS.map(({ key, label, icon: Icon, money, tone }) => (
        <Card size="sm" key={key}>
          <CardContent className="flex flex-col gap-1">
            <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
              <Icon aria-hidden className="size-3.5" />
              {label}
            </div>
            {isLoading || !metrics ? (
              <Skeleton data-testid="metric-skeleton" className="h-7 w-24" />
            ) : (
              <p className={`text-2xl font-semibold tracking-tight ${tone}`}>
                {money ? formatGHS(metrics[key]) : metrics[key]}
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
