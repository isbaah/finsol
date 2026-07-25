import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export default function ForgotPasswordPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-12">
      <div className="flex w-full max-w-sm flex-col gap-1 text-center">
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">
          Forgot your password?
        </h1>
        <p className="text-muted-foreground text-sm">
          Enter your email and we&apos;ll send you a reset link.
        </p>
      </div>
      <ForgotPasswordForm />
    </main>
  );
}
