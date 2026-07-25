import * as React from "react";

import { cn } from "@/lib/utils";

/** Plain native <select>, styled to match Input — not Base UI's Select
 * primitive. A native element registers directly with react-hook-form
 * without needing a Controller wrapper, and needs no accessibility work of
 * its own (unlike Checkbox, which required one — see signup-form.tsx). */
function Select({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      data-slot="select"
      className={cn(
        "border-input focus-visible:border-ring focus-visible:ring-ring/30 disabled:bg-input/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 bg-card h-11 w-full min-w-0 rounded-xl border px-3.5 py-1 text-base transition-all duration-200 outline-none focus-visible:ring-3 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:ring-3 md:text-sm",
        className,
      )}
      {...props}
    />
  );
}

export { Select };
