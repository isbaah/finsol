"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { login } from "@/features/auth/api";
import { applyAllauthErrors } from "@/features/auth/errors";
import { useInvalidateSession } from "@/features/auth/use-session";
import { type LoginFormValues, loginSchema } from "@/schemas/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginForm() {
  const router = useRouter();
  const invalidateSession = useInvalidateSession();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginFormValues) => {
    setSubmitError(null);
    const response = await login(values.email, values.password);

    if (response.meta?.is_authenticated) {
      invalidateSession();
      toast.success("Signed in.");
      router.push("/dashboard");
      return;
    }

    if (response.status === 409) {
      // Already have an authenticated session (e.g. a stale tab) — allauth
      // refuses to process another login rather than erroring.
      invalidateSession();
      toast.success("You're already signed in.");
      router.push("/dashboard");
      return;
    }

    if (response.errors?.length) {
      applyAllauthErrors(response.errors, setError, "password");
      return;
    }

    const pending = response.data?.flows?.find((flow) => flow.is_pending);
    if (pending?.id === "verify_email") {
      setSubmitError("Please verify your email address before signing in.");
      return;
    }

    setSubmitError("Could not sign you in. Check your email and password and try again.");
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex w-full max-w-sm flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" autoComplete="email" {...register("email")} />
        {errors.email && <p className="text-destructive text-sm">{errors.email.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
        />
        {errors.password && <p className="text-destructive text-sm">{errors.password.message}</p>}
      </div>
      {submitError && <p className="text-destructive text-sm">{submitError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Signing in…" : "Sign in"}
      </Button>
      <div className="text-muted-foreground flex justify-between text-sm">
        <Link href="/auth/forgot-password" className="hover:text-foreground">
          Forgot password?
        </Link>
        <Link href="/auth/signup" className="hover:text-foreground">
          Create an account
        </Link>
      </div>
    </form>
  );
}
