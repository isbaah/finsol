"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { signup } from "@/features/auth/api";
import { applyAllauthErrors } from "@/features/auth/errors";
import { useInvalidateSession } from "@/features/auth/use-session";
import { type SignupFormValues, signupSchema } from "@/schemas/auth";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function SignupForm() {
  const router = useRouter();
  const invalidateSession = useInvalidateSession();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [signedUpEmail, setSignedUpEmail] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormValues>({ resolver: zodResolver(signupSchema) });

  const onSubmit = async (values: SignupFormValues) => {
    setSubmitError(null);
    const response = await signup(values.email, values.password);

    if (response.status === 409) {
      // Already have an authenticated session — allauth refuses to process
      // a signup rather than erroring.
      invalidateSession();
      toast.success("You're already signed in.");
      router.push("/dashboard");
      return;
    }

    if (response.errors?.length) {
      applyAllauthErrors(response.errors, setError, "email");
      return;
    }

    const pending = response.data?.flows?.find((flow) => flow.is_pending);
    if (pending?.id === "verify_email" || response.meta?.is_authenticated) {
      setSignedUpEmail(values.email);
      return;
    }

    setSubmitError("Something went wrong creating your account. Please try again.");
  };

  if (signedUpEmail) {
    return (
      <div className="flex w-full max-w-sm flex-col gap-2 text-center">
        <h2 className="text-foreground text-lg font-semibold">Check your email</h2>
        <p className="text-muted-foreground text-sm">
          We sent a verification link to <span className="font-medium">{signedUpEmail}</span>. Open
          it to activate your account.
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
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
        />
        {errors.password && <p className="text-destructive text-sm">{errors.password.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="confirmPassword">Confirm password</Label>
        <Input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          {...register("confirmPassword")}
        />
        {errors.confirmPassword && (
          <p className="text-destructive text-sm">{errors.confirmPassword.message}</p>
        )}
      </div>
      <Controller<SignupFormValues, "declaration">
        control={control}
        name="declaration"
        render={({ field }) => (
          <div className="flex items-start gap-2">
            <Checkbox
              id="declaration"
              checked={field.value ?? false}
              onCheckedChange={(checked) => field.onChange(checked)}
            />
            <Label htmlFor="declaration" className="text-muted-foreground text-sm font-normal">
              The information I provide is accurate. I understand a lender administrator determines
              the final terms of any loan offer.
            </Label>
          </div>
        )}
      />
      {errors.declaration && (
        <p className="text-destructive text-sm">{errors.declaration.message}</p>
      )}
      {submitError && <p className="text-destructive text-sm">{submitError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-muted-foreground text-center text-sm">
        Already have an account?{" "}
        <Link href="/auth/login" className="text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
