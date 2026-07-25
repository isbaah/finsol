"use client";

import { useState } from "react";
import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { requestPasswordReset } from "@/features/auth/api";
import { type ForgotPasswordFormValues, forgotPasswordSchema } from "@/schemas/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ForgotPasswordForm() {
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = async (values: ForgotPasswordFormValues) => {
    // Always show the same confirmation regardless of whether the address
    // exists — the backend intentionally sends a generic 200 either way
    // (see backend/tests/test_auth.py's anti-enumeration test).
    await requestPasswordReset(values.email);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="flex w-full max-w-sm flex-col gap-2 text-center">
        <h2 className="text-foreground text-lg font-semibold">Check your email</h2>
        <p className="text-muted-foreground text-sm">
          If an account exists for that address, we&apos;ve sent instructions to reset the password.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex w-full max-w-sm flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" autoComplete="email" {...register("email")} />
        {errors.email && <p className="text-destructive text-sm">{errors.email.message}</p>}
      </div>
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Sending…" : "Send reset link"}
      </Button>
      <p className="text-muted-foreground text-center text-sm">
        <Link href="/auth/login" className="hover:text-foreground">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
