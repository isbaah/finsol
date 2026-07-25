import { ProfileForm } from "@/components/profile/profile-form";

export default function OnboardingProfilePage() {
  return (
    <main className="flex flex-1 flex-col items-center gap-6 px-6 py-12">
      <div className="flex w-full max-w-md flex-col gap-1 text-center">
        <h1 className="text-foreground text-2xl font-semibold tracking-tight">
          Complete your profile
        </h1>
        <p className="text-muted-foreground text-sm">
          We need your phone number and payout details before you can request a loan.
        </p>
      </div>
      <ProfileForm />
    </main>
  );
}
