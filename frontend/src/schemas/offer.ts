import { z } from "zod";

// Same principal/rate/term/date fields as schemas/amortization.ts (the
// offer form is built on the same preview pipeline, Stage 7), plus the
// fields the preview never needed.
export const offerSchema = z.object({
  principal: z
    .string()
    .min(1, "Principal is required.")
    .refine((v) => Number(v) > 0, "Principal must be greater than zero."),
  interest_rate_percent: z
    .string()
    .min(1, "Interest rate is required.")
    .refine((v) => Number(v) >= 0, "Interest rate cannot be negative."),
  term_count: z
    .number({ message: "Term count is required." })
    .int("Term count must be a whole number.")
    .min(1, "Term count must be at least 1.")
    .max(60, "Term count cannot exceed 60."),
  term_unit: z.enum(["WEEK", "MONTH"], { message: "Choose a term unit." }),
  first_due_date: z.string().min(1, "First due date is required."),
  offer_expiry_date: z.string().optional(),
  customer_terms: z.string().optional(),
  internal_notes: z.string().optional(),
});

export type OfferFormValues = z.infer<typeof offerSchema>;
