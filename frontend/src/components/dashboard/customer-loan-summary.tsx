"use client";

import { useState } from "react";
import Link from "next/link";

import { InstallmentStatusBadge } from "@/components/loans/installment-status-badge";
import { LoanStatusBadge } from "@/components/loans/loan-status-badge";
import { InstallmentDetailDialog } from "@/components/repayments/installment-detail-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAgreement } from "@/features/agreements/use-agreements";
import type { CustomerLoan, RepaymentInstallmentSummary } from "@/features/loans/types";
import { formatDate, formatGHS } from "@/lib/format";

const OPEN_INSTALLMENT_STATUSES = ["UPCOMING", "DUE", "PARTIALLY_PAID", "OVERDUE"];

/** Section 15's customer active-loan summary: principal, repaid,
 * outstanding, next payment, compact schedule, recent payments, and the
 * agreement download — everything read straight off CustomerLoanSerializer,
 * nothing recomputed client-side. */
export function CustomerLoanSummary({ loan }: { loan: CustomerLoan }) {
  const { data: agreement } = useAgreement(loan.agreement_id);
  const [selectedInstallment, setSelectedInstallment] =
    useState<RepaymentInstallmentSummary | null>(null);

  const nextInstallment = loan.installments.find((installment) =>
    OPEN_INSTALLMENT_STATUSES.includes(installment.status),
  );
  const compactSchedule = loan.installments.slice(0, 4);
  const recentPayments = loan.payments.filter((payment) => payment.status === "POSTED").slice(0, 3);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your loan — {loan.loan_number}</CardTitle>
        <CardAction>
          <LoanStatusBadge status={loan.status} />
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <dt className="text-muted-foreground text-xs">Principal</dt>
            <dd className="text-foreground text-lg font-semibold">{formatGHS(loan.principal)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Repaid so far</dt>
            <dd className="text-lg font-semibold text-emerald-700 dark:text-emerald-400">
              {formatGHS(loan.amount_repaid)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Outstanding</dt>
            <dd className="text-foreground text-lg font-semibold">
              {formatGHS(loan.outstanding_balance)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Next payment</dt>
            <dd className="text-foreground text-lg font-semibold">
              {nextInstallment ? formatGHS(nextInstallment.outstanding_amount) : "—"}
            </dd>
            {nextInstallment && (
              <p className="text-muted-foreground text-xs">
                due {formatDate(nextInstallment.due_date)}
              </p>
            )}
          </div>
        </dl>

        {compactSchedule.length > 0 && (
          <div>
            <h3 className="text-foreground mb-1 text-xs font-semibold">Repayment schedule</h3>
            <p className="text-muted-foreground mb-1 text-xs">
              Click an installment for payment details and where to pay.
            </p>
            <ul className="divide-border border-border divide-y rounded-lg border">
              {compactSchedule.map((installment) => (
                <li key={installment.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedInstallment(installment)}
                    className="hover:bg-muted/60 flex w-full items-center justify-between gap-3 px-3 py-1.5 text-left text-sm transition-colors"
                  >
                    <span className="text-muted-foreground">
                      #{installment.sequence_number} — {formatDate(installment.due_date)}
                    </span>
                    <span className="flex items-center gap-2">
                      <span className="text-foreground font-medium">
                        {formatGHS(installment.total_due)}
                      </span>
                      <InstallmentStatusBadge status={installment.status} />
                    </span>
                  </button>
                </li>
              ))}
              {loan.installments.length > compactSchedule.length && (
                <li className="text-muted-foreground px-3 py-1.5 text-xs">
                  {loan.installments.length - compactSchedule.length} more installment(s) — see the
                  full schedule on the loan page.
                </li>
              )}
            </ul>
            <InstallmentDetailDialog
              loanId={loan.id}
              installment={selectedInstallment}
              open={selectedInstallment !== null}
              onOpenChange={(dialogOpen) => {
                if (!dialogOpen) setSelectedInstallment(null);
              }}
            />
          </div>
        )}

        {recentPayments.length > 0 && (
          <div>
            <h3 className="text-foreground mb-1 text-xs font-semibold">Recent payments</h3>
            <ul className="divide-border border-border divide-y rounded-lg border">
              {recentPayments.map((payment) => (
                <li
                  key={payment.id}
                  className="flex items-center justify-between gap-3 px-3 py-1.5 text-sm"
                >
                  <span className="text-muted-foreground">
                    {formatDate(payment.payment_date)} — {payment.receipt_number}
                  </span>
                  <span className="font-medium text-emerald-700 dark:text-emerald-400">
                    {formatGHS(payment.amount)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            nativeButton={false}
            render={<Link href={`/loans/${loan.id}`}>View full loan</Link>}
          />
          {agreement && (
            <Button
              size="sm"
              variant="outline"
              nativeButton={false}
              render={
                <a href={agreement.download_url} target="_blank" rel="noopener noreferrer">
                  Download agreement (PDF)
                </a>
              }
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}
