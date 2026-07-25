import Link from "next/link";
import { ArrowRightIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      {/* Apple hero grammar: oversized tight-tracked headline, airy lead
          copy, one blue capsule CTA plus a quiet text link. */}
      <section className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-24 text-center">
        <p className="text-primary text-sm font-semibold tracking-wide">Finsol</p>
        <h1 className="text-foreground max-w-2xl text-5xl leading-[1.07] font-semibold tracking-[-0.015em] sm:text-6xl">
          Borrowing, without the back and forth.
        </h1>
        <p className="text-muted-foreground max-w-xl text-lg leading-relaxed font-light sm:text-xl">
          Request a loan, review your offer, sign digitally, and track every repayment — all in
          one calm, clear place.
        </p>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-4">
          <Button
            size="lg"
            nativeButton={false}
            render={<Link href="/auth/signup">Get started</Link>}
          />
          <Link
            href="/auth/login"
            className="text-primary inline-flex items-center gap-1 text-[0.95rem] hover:underline"
          >
            Sign in
            <ArrowRightIcon aria-hidden className="size-4" />
          </Link>
        </div>
      </section>

      <section className="border-border bg-card border-t px-6 py-16">
        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-10 text-center sm:grid-cols-3">
          <div className="flex flex-col gap-1.5">
            <h2 className="text-foreground text-base font-semibold tracking-tight">
              Clear offers
            </h2>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Total repayable, every installment, and every date — shown before you sign.
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <h2 className="text-foreground text-base font-semibold tracking-tight">
              Sign digitally
            </h2>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Accept with a drawn signature and download your agreement as a PDF.
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <h2 className="text-foreground text-base font-semibold tracking-tight">
              Stay on track
            </h2>
            <p className="text-muted-foreground text-sm leading-relaxed">
              SMS reminders before every due date, and a live view of what&apos;s left.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
