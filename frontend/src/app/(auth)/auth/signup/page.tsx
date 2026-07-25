import { SignupForm } from "@/components/auth/signup-form";
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";

export default function SignupPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-12">
      <div className="flex w-full max-w-sm flex-col gap-1 text-center">
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Create an account</h1>
        <p className="text-muted-foreground text-sm">
          Sign up with your email, or continue with Google.
        </p>
      </div>
      <SignupForm />
      <div className="flex w-full max-w-sm items-center gap-3">
        <div className="bg-border h-px flex-1" />
        <span className="text-muted-foreground text-xs">OR</span>
        <div className="bg-border h-px flex-1" />
      </div>
      <GoogleSignInButton />
    </main>
  );
}
