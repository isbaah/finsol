export default function AdminDashboardPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
      <h1 className="text-foreground text-xl font-semibold tracking-tight">Admin dashboard</h1>
      <p className="text-muted-foreground max-w-sm text-sm">
        Portfolio KPIs, requests, offers, and repayments queues arrive in Stages 7, 9, 10, and 12.
      </p>
    </main>
  );
}
