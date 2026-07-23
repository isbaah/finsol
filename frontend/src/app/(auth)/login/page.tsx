export default function LoginPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
      <h1 className="text-foreground text-xl font-semibold tracking-tight">Sign in</h1>
      <p className="text-muted-foreground max-w-sm text-sm">
        Email/password and Google sign-in arrive in Stage 2 (django-allauth headless integration).
      </p>
    </main>
  );
}
