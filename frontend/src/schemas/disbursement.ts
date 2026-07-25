import { z } from "zod";

export const disbursementSchema = z.object({
  amount: z
    .string()
    .min(1, "Amount is required.")
    .refine((v) => Number(v) > 0, "Amount must be greater than zero."),
  method: z.enum(["MOBILE_MONEY", "BANK"], { message: "Choose a disbursement method." }),
  external_transaction_reference: z.string().optional(),
  notes: z.string().optional(),
});

export type DisbursementFormValues = z.infer<typeof disbursementSchema>;
