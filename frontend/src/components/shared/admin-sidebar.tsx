"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboardIcon,
  InboxIcon,
  LandmarkIcon,
  MessageSquareIcon,
  SettingsIcon,
  UsersIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

/** Section 16's compact admin sidebar, painted in the accent blue (matching
 * the navbar) against the white content canvas. Active item is a white
 * capsule with blue text. Only destinations that exist today are listed;
 * Reports, Audit Log, and Settings arrive with Stages 13/14. */
const NAV_ITEMS = [
  { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboardIcon },
  { href: "/admin/loan-requests", label: "Loan Requests", icon: InboxIcon },
  { href: "/admin/loans", label: "Loans", icon: LandmarkIcon },
  { href: "/admin/customers", label: "Customers", icon: UsersIcon },
  { href: "/admin/sms-activity", label: "SMS Activity", icon: MessageSquareIcon },
  { href: "/admin/settings", label: "Settings", icon: SettingsIcon },
];

function navLinkClassName(active: boolean) {
  return cn(
    "flex items-center gap-2.5 rounded-full px-4 py-2 text-sm font-medium transition-all duration-200",
    active
      ? "bg-primary-foreground text-primary"
      : "text-primary-foreground/75 hover:bg-primary-foreground/10 hover:text-primary-foreground",
  );
}

export function AdminSidebar() {
  const pathname = usePathname();
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <>
      {/* Desktop: persistent accent-colored left sidebar */}
      <aside className="bg-primary hidden w-60 shrink-0 md:block">
        <nav aria-label="Admin navigation" className="sticky top-16 flex flex-col gap-1 p-4 pt-6">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={isActive(href) ? "page" : undefined}
              className={navLinkClassName(isActive(href))}
            >
              <Icon aria-hidden className="size-4" strokeWidth={isActive(href) ? 2.25 : 2} />
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Mobile / tablet: accent horizontal nav below the header */}
      <nav
        aria-label="Admin navigation"
        className="bg-primary flex gap-1 overflow-x-auto px-4 py-2 md:hidden"
      >
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={isActive(href) ? "page" : undefined}
            className={cn(navLinkClassName(isActive(href)), "whitespace-nowrap")}
          >
            <Icon aria-hidden className="size-4" />
            {label}
          </Link>
        ))}
      </nav>
    </>
  );
}
