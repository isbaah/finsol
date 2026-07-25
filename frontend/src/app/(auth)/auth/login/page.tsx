import { LoginForm } from "@/components/auth/login-form";
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-12">
      <div className="flex w-full max-w-sm flex-col gap-1 text-center">
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="text-muted-foreground text-sm">Welcome back.</p>
      </div>
      {error === "social" && (
        <p className="text-destructive w-full max-w-sm text-center text-sm">
          We couldn&apos;t sign you in with Google. Please try again or use your email and password.
        </p>
      )}
      <LoginForm />
      <div className="flex w-full max-w-sm items-center gap-3">
        <div className="bg-border h-px flex-1" />
        <span className="text-muted-foreground text-xs">OR</span>
        <div className="bg-border h-px flex-1" />
      </div>
      <GoogleSignInButton />
    </main>
  );
}
