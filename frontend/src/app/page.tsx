import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-foreground text-2xl font-semibold tracking-tight">
        Loan Management System
      </h1>
      <p className="text-muted-foreground max-w-md text-sm">
        Request a loan, review your offer, and track repayments in one place. This project is under
        active, stage-gated development — see docs/BUILD_PROGRESS.md in the repository for current
        status.
      </p>
      <Button nativeButton={false} render={<Link href="/login">Sign in</Link>} />
    </main>
  );
}
