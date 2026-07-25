"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { resetPassword } from "@/features/auth/api";
import { useInvalidateSession } from "@/features/auth/use-session";
import { type ResetPasswordFormValues, resetPasswordSchema } from "@/schemas/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ResetPasswordForm({ resetKey }: { resetKey: string }) {
  const router = useRouter();
  const invalidateSession = useInvalidateSession();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({ resolver: zodResolver(resetPasswordSchema) });

  const onSubmit = async (values: ResetPasswordFormValues) => {
    setSubmitError(null);
    const response = await resetPassword(resetKey, values.password);

    if (response.status === 200) {
      invalidateSession();
      toast.success("Password reset.");
      router.push(response.meta?.is_authenticated ? "/dashboard" : "/auth/login");
      return;
    }

    setSubmitError(
      "This reset link is invalid or has expired. Request a new one from the forgot password page.",
    );
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex w-full max-w-sm flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">New password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
        />
        {errors.password && <p className="text-destructive text-sm">{errors.password.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="confirmPassword">Confirm new password</Label>
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
      {submitError && <p className="text-destructive text-sm">{submitError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Resetting…" : "Reset password"}
      </Button>
    </form>
  );
}
