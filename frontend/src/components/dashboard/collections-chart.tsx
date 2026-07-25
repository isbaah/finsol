"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCollectionsChart } from "@/features/dashboards/use-dashboards";
import type { ChartMonths } from "@/features/dashboards/types";
import { formatGHS } from "@/lib/format";

const MONTH_LABEL = new Intl.DateTimeFormat("en-GB", { month: "short", year: "2-digit" });

function monthLabel(isoMonth: string) {
  const [year, month] = isoMonth.split("-").map(Number);
  return MONTH_LABEL.format(new Date(year, month - 1, 1));
}

/** Section 16's expected-versus-collected monthly chart, with six- and
 * twelve-month views. The backend computes both series; this component only
 * renders them. */
export function CollectionsChart() {
  const [months, setMonths] = useState<ChartMonths>(6);
  const { data, isLoading, isError } = useCollectionsChart(months);

  const rows = (data ?? []).map((row) => ({
    month: monthLabel(row.month),
    Expected: Number(row.expected),
    Collected: Number(row.collected),
  }));
  const hasActivity = rows.some((row) => row.Expected > 0 || row.Collected > 0);

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Expected vs collected</CardTitle>
        <CardAction>
          <div role="group" aria-label="Chart window" className="flex gap-1">
            {([6, 12] as const).map((option) => (
              <Button
                key={option}
                size="sm"
                variant={months === option ? "default" : "outline"}
                aria-pressed={months === option}
                onClick={() => setMonths(option)}
              >
                {option} months
              </Button>
            ))}
          </div>
        </CardAction>
      </CardHeader>
      <CardContent>
        {isError && (
          <p className="text-destructive text-sm">Couldn&apos;t load the chart. Please try again.</p>
        )}
        {isLoading && <Skeleton data-testid="chart-skeleton" className="h-64 w-full" />}
        {!isLoading && !isError && !hasActivity && (
          <p className="text-muted-foreground py-16 text-center text-sm">
            No repayments were expected or collected in the last {months} months. Activity appears
            here once loans are disbursed and repayments start arriving.
          </p>
        )}
        {!isLoading && !isError && hasActivity && (
          <div className="h-64 w-full" role="img" aria-label="Bar chart of expected versus collected repayments by month, in Ghana cedis">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} accessibilityLayer>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="month"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  width={70}
                  tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                  tickFormatter={(value: number) => formatGHS(value)}
                />
                <Tooltip
                  formatter={(value) => formatGHS(Number(value))}
                  cursor={{ fill: "var(--muted)" }}
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "0.875rem",
                    color: "var(--foreground)",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Expected" fill="var(--muted-foreground)" radius={[5, 5, 0, 0]} />
                <Bar dataKey="Collected" fill="var(--primary)" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
