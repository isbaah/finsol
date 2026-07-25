import { VerifyEmailStatus } from "@/components/auth/verify-email-status";

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ key?: string }>;
}) {
  const { key } = await searchParams;

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-12 text-center">
      <h1 className="text-foreground text-2xl font-semibold tracking-tight">Email verification</h1>
      <VerifyEmailStatus verificationKey={key ?? null} />
    </main>
  );
}
