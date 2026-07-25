"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { logout } from "@/features/auth/api";
import { useInvalidateSession, useSession } from "@/features/auth/use-session";
import { Button } from "@/components/ui/button";

/** `tone="accent"` renders white-on-blue for the accent-colored navbar. */
export function UserMenu({ tone = "default" }: { tone?: "default" | "accent" }) {
  const router = useRouter();
  const invalidateSession = useInvalidateSession();
  const { data } = useSession();

  const handleSignOut = async () => {
    await logout();
    invalidateSession();
    toast.success("Signed out.");
    router.push("/auth/login");
  };

  if (!data?.user) return null;

  const onAccent = tone === "accent";

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className={onAccent ? "text-primary-foreground/80" : "text-muted-foreground"}>
        {data.user.email}
      </span>
      <Button
        variant="outline"
        size="sm"
        className={
          onAccent
            ? "border-primary-foreground/40 text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
            : undefined
        }
        onClick={handleSignOut}
      >
        Sign out
      </Button>
    </div>
  );
}
