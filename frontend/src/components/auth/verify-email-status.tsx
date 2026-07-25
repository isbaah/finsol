"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { verifyEmail } from "@/features/auth/api";
import { useInvalidateSession } from "@/features/auth/use-session";
import { Button } from "@/components/ui/button";

type Status = "verifying" | "success" | "error";

export function VerifyEmailStatus({ verificationKey }: { verificationKey: string | null }) {
  const router = useRouter();
  const invalidateSession = useInvalidateSession();
  const [status, setStatus] = useState<Status>(verificationKey ? "verifying" : "error");
  const attempted = useRef(false);

  useEffect(() => {
    if (!verificationKey || attempted.current) return;
    attempted.current = true;

    verifyEmail(verificationKey).then((response) => {
      if (response.status === 200) {
        invalidateSession();
        setStatus("success");
        const timer = setTimeout(() => {
          router.push(response.meta?.is_authenticated ? "/dashboard" : "/auth/login");
        }, 1500);
        return () => clearTimeout(timer);
      }
      setStatus("error");
    });
  }, [verificationKey, invalidateSession, router]);

  if (status === "verifying") {
    return <p className="text-muted-foreground text-sm">Verifying your email…</p>;
  }

  if (status === "success") {
    return (
      <p className="text-muted-foreground text-sm">
        Your email is verified. Taking you to your dashboard…
      </p>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <p className="text-destructive text-sm">This verification link is invalid or has expired.</p>
      <Button render={<Link href="/auth/login">Back to sign in</Link>} />
    </div>
  );
}
