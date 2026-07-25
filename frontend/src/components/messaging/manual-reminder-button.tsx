"use client";

import { useState } from "react";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useSendManualReminder } from "@/features/messaging/use-messaging";

/** Section 16's upcoming-repayments-table "Send SMS now" action / Section
 * 17's MANUAL_REMINDER type — exempt from the scheduled-reminder
 * uniqueness constraint, so it may be sent more than once, but always
 * records the admin actor and an optional reason. */
export function ManualReminderButton({ installmentId }: { installmentId: string }) {
  const sendReminder = useSendManualReminder();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const handleSend = async () => {
    setError(null);
    try {
      await sendReminder.mutateAsync({ installmentId, reason });
      setSent(true);
      setTimeout(() => {
        setOpen(false);
        setSent(false);
        setReason("");
      }, 900);
    } catch {
      setError("Couldn't send this reminder. Please try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm">
            Send reminder
          </Button>
        }
      />
      <DialogContent>
        <DialogTitle>Send a manual reminder</DialogTitle>
        <DialogDescription>
          This sends an SMS immediately and records who sent it, regardless of the scheduled
          reminder windows.
        </DialogDescription>
        <div className="mt-4 flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="reason">Reason (optional)</Label>
            <Textarea
              id="reason"
              rows={2}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </div>
          {error && <p className="text-destructive text-sm">{error}</p>}
          {sent && <p className="text-sm text-emerald-700 dark:text-emerald-400">Reminder sent.</p>}
          <div className="flex justify-end gap-2">
            <DialogClose
              render={
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              }
            />
            <Button type="button" onClick={handleSend} disabled={sendReminder.isPending}>
              {sendReminder.isPending ? "Sending…" : "Send reminder"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
