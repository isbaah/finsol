import { z } from "zod";

// Client-side preview only — the backend's own calculate() is the
// authoritative validator (Section 14: "Validate on both frontend and
// backend, with backend authoritative"). Field names match the API 1:1,
// same reasoning as schemas/profile.ts.
export const amortizationPreviewSchema = z.object({
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
});

export type AmortizationPreviewFormValues = z.infer<typeof amortizationPreviewSchema>;
