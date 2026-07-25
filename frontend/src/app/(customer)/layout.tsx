import Link from "next/link";

import { CustomerAreaGuard } from "@/components/shared/customer-area-guard";
import { UserMenu } from "@/components/shared/user-menu";

export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <header className="bg-primary sticky top-0 z-40 flex items-center justify-between gap-4 px-6 py-3 shadow-[0_2px_10px_rgb(0_0_0/0.18)]">
        <div className="flex items-center gap-6">
          <Link
            href="/dashboard"
            className="text-primary-foreground text-sm font-semibold tracking-tight"
          >
            Finsol
          </Link>
          <nav aria-label="Customer navigation" className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="text-primary-foreground/75 hover:text-primary-foreground text-sm transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/requests"
              className="text-primary-foreground/75 hover:text-primary-foreground text-sm transition-colors"
            >
              My requests
            </Link>
            <Link
              href="/profile"
              className="text-primary-foreground/75 hover:text-primary-foreground text-sm transition-colors"
            >
              Profile
            </Link>
          </nav>
        </div>
        <UserMenu tone="accent" />
      </header>
      <CustomerAreaGuard>{children}</CustomerAreaGuard>
    </div>
  );
}
