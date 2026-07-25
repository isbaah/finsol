import { AdminSidebar } from "@/components/shared/admin-sidebar";
import { StaffAreaGuard } from "@/components/shared/staff-area-guard";
import { UserMenu } from "@/components/shared/user-menu";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      {/* Accent navbar: the single blue carries the app chrome, content
          stays white. */}
      {/* Small drop shadow so the header reads as its own layer above the
          same-colored sidebar. */}
      <header className="bg-primary sticky top-0 z-40 flex items-center justify-between px-6 py-3 shadow-[0_2px_10px_rgb(0_0_0/0.18)]">
        <span className="text-primary-foreground text-sm font-semibold tracking-tight">
          Finsol <span className="text-primary-foreground/70 font-normal">Admin</span>
        </span>
        <UserMenu tone="accent" />
      </header>
      {/* Column on mobile (nav strip above the page), row on desktop
          (persistent sidebar beside it) — AdminSidebar renders the right
          variant for each breakpoint. */}
      <div className="flex flex-1 flex-col md:flex-row">
        <AdminSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <StaffAreaGuard>{children}</StaffAreaGuard>
        </div>
      </div>
    </div>
  );
}
