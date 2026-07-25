import { BackButton } from "@/components/shared/back-button";
import { ProfileForm } from "@/components/profile/profile-form";

export default function ProfilePage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-6">
      <BackButton fallbackHref="/dashboard" label="Dashboard" />
      <div>
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">Your profile</h1>
        <p className="text-muted-foreground text-sm">
          Your name, contact details, and where we send your money when a loan is disbursed.
        </p>
      </div>
      <ProfileForm />
    </main>
  );
}
