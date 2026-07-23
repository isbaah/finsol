export default function CustomerDashboardPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
      <h1 className="text-foreground text-xl font-semibold tracking-tight">Customer dashboard</h1>
      <p className="text-muted-foreground max-w-sm text-sm">
        Loan request status, active loan summary, and repayment schedule arrive in Stages 6, 8, and
        12.
      </p>
    </main>
  );
}
