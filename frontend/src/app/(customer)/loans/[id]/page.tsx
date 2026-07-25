"use client";

import { use, useState } from "react";

import { BackButton } from "@/components/shared/back-button";
import { InstallmentStatusBadge } from "@/components/loans/installment-status-badge";
import { LoanStatusBadge } from "@/components/loans/loan-status-badge";
import { InstallmentDetailDialog } from "@/components/repayments/installment-detail-dialog";
import { PaymentHistoryTable } from "@/components/repayments/payment-history-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAgreement } from "@/features/agreements/use-agreements";
import { useCustomerLoan } from "@/features/loans/use-loans";
import type { RepaymentInstallmentSummary } from "@/features/loans/types";
import { formatDate, formatDateTime, formatGHS } from "@/lib/format";

export default function CustomerLoanDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: loan, isLoading, isError } = useCustomerLoan(id);
  const { data: agreement } = useAgreement(loan?.agreement_id ?? "");
  const [selectedInstallment, setSelectedInstallment] =
    useState<RepaymentInstallmentSummary | null>(null);

  if (isLoading) return <p className="text-muted-foreground p-6 text-sm">Loading…</p>;
  if (isError || !loan) {
    return <p className="text-destructive p-6 text-sm">Couldn&apos;t load this loan.</p>;
  }

  return (
    <main className="flex flex-1 flex-col gap-6 p-6">
      <BackButton fallbackHref="/dashboard" label="Dashboard" />
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-foreground text-2xl font-semibold tracking-tight">
            {loan.loan_number}
          </h1>
          <p className="text-muted-foreground text-sm">Request {loan.request_number}</p>
        </div>
        <LoanStatusBadge status={loan.status} />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Principal</p>
            <p className="text-foreground text-lg font-semibold">{formatGHS(loan.principal)}</p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Total repayable</p>
            <p className="text-foreground text-lg font-semibold">
              {formatGHS(loan.total_repayable)}
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Disbursed</p>
            <p className="text-foreground text-lg font-semibold">
              {formatGHS(loan.amount_disbursed)}
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <p className="text-muted-foreground text-xs">Outstanding</p>
            <p className="text-foreground text-lg font-semibold">
              {formatGHS(loan.outstanding_balance)}
            </p>
          </CardContent>
        </Card>
      </div>

      {agreement && (
        <Card size="sm" className="max-w-md">
          <CardContent className="flex flex-col gap-2">
            <p className="text-muted-foreground text-xs">Loan agreement</p>
            <p className="text-foreground text-sm">
              Signed by {agreement.typed_legal_name} on {formatDateTime(agreement.accepted_at)}
            </p>
            <Button
              variant="outline"
              nativeButton={false}
              render={
                <a href={agreement.download_url} target="_blank" rel="noopener noreferrer">
                  Download agreement (PDF)
                </a>
              }
            />
          </CardContent>
        </Card>
      )}

      {loan.installments.length > 0 && (
        <div>
          <h2 className="text-foreground mb-2 text-base font-semibold tracking-tight">Repayment schedule</h2>
          <p className="text-muted-foreground mb-2 text-sm">
            Click an installment to see its payment details — and tell us once you&apos;ve paid.
          </p>
          <div className="bg-card ring-border shadow-card overflow-x-auto rounded-[1.125rem] ring-1">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-border text-muted-foreground border-b text-left">
                  <th className="px-5 py-3 font-medium">#</th>
                  <th className="px-5 py-3 font-medium">Due date</th>
                  <th className="px-5 py-3 font-medium">Total due</th>
                  <th className="px-5 py-3 font-medium">Outstanding</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">
                    <span className="sr-only">Details</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {loan.installments.map((installment) => (
                  <tr
                    key={installment.sequence_number}
                    onClick={() => setSelectedInstallment(installment)}
                    className="border-border hover:bg-muted/60 border-b cursor-pointer transition-colors last:border-0"
                  >
                    <td className="px-5 py-3">{installment.sequence_number}</td>
                    <td className="px-5 py-3">{formatDate(installment.due_date)}</td>
                    <td className="px-5 py-3">{formatGHS(installment.total_due)}</td>
                    <td className="px-5 py-3">{formatGHS(installment.outstanding_amount)}</td>
                    <td className="px-5 py-3">
                      <InstallmentStatusBadge status={installment.status} />
                    </td>
                    <td className="px-5 py-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedInstallment(installment);
                        }}
                      >
                        Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <InstallmentDetailDialog
            loanId={loan.id}
            installment={selectedInstallment}
            open={selectedInstallment !== null}
            onOpenChange={(open) => {
              if (!open) setSelectedInstallment(null);
            }}
          />
        </div>
      )}

      {loan.payments.length > 0 && (
        <div>
          <h2 className="text-foreground mb-2 text-base font-semibold tracking-tight">Payment history</h2>
          <PaymentHistoryTable loanId={loan.id} payments={loan.payments} showActions={false} />
        </div>
      )}
    </main>
  );
}
