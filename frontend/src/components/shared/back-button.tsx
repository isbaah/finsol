"use client";

import { useRouter } from "next/navigation";
import { ChevronLeftIcon } from "lucide-react";

/** Quiet Apple-style back control for sub-pages. Uses real browser history
 * when there is any (so it behaves like the native back button), otherwise
 * falls back to a sensible parent page — covers deep links and refreshes. */
export function BackButton({
  fallbackHref = "/dashboard",
  label = "Back",
}: {
  fallbackHref?: string;
  label?: string;
}) {
  const router = useRouter();

  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push(fallbackHref);
    }
  };

  return (
    <button
      type="button"
      onClick={handleBack}
      className="text-primary -ml-1.5 inline-flex w-fit items-center gap-0.5 rounded-full px-1.5 py-1 text-sm transition-colors hover:underline"
    >
      <ChevronLeftIcon aria-hidden className="size-4" />
      {label}
    </button>
  );
}
