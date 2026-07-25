import { z } from "zod";

export const repaymentSchema = z.object({
  amount: z
    .string()
    .min(1, "Amount is required.")
    .refine((v) => Number(v) > 0, "Amount must be greater than zero."),
  payment_date: z.string().min(1, "Payment date is required."),
  payment_method: z.enum(["MOBILE_MONEY", "BANK", "CASH", "OTHER"], {
    message: "Choose a payment method.",
  }),
  external_transaction_reference: z.string().optional(),
  notes: z.string().optional(),
});

export type RepaymentFormValues = z.infer<typeof repaymentSchema>;

export const reversalSchema = z.object({
  reason: z.string().min(1, "A reason is required to reverse a payment."),
});

export type ReversalFormValues = z.infer<typeof reversalSchema>;
