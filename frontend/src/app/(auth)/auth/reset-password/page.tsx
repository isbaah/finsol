import Link from "next/link";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ key?: string }>;
}) {
  const { key } = await searchParams;

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-12">
      <div className="flex w-full max-w-sm flex-col gap-1 text-center">
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Reset password</h1>
      </div>
      {key ? (
        <ResetPasswordForm resetKey={key} />
      ) : (
        <p className="text-destructive max-w-sm text-center text-sm">
          This link is missing its reset key.{" "}
          <Link href="/auth/forgot-password" className="text-primary hover:underline">
            Request a new one
          </Link>
          .
        </p>
      )}
    </main>
  );
}
