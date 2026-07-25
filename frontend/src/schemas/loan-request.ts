import { z } from "zod";

// Field names match the API 1:1, same reasoning as schemas/profile.ts.
// requested_term_count/unit are optional (Section 15: "preferred term
// count" / "preferred term unit" — a preference, not a binding request;
// the officer sets the real terms in the offer).
export const loanRequestSchema = z.object({
  requested_amount: z
    .string()
    .min(1, "Requested amount is required.")
    .refine((v) => Number(v) > 0, "Requested amount must be greater than zero."),
  purpose: z.string().min(1, "Tell us what the loan is for."),
  // Plain z.number().optional(), not z.preprocess/z.coerce — those change
  // this field's *input* type to unknown, which breaks useForm's resolver
  // typing (the same z.infer-vs-z.input mismatch documented in
  // schemas/amortization.ts). The empty-input-produces-NaN problem this
  // would otherwise need preprocess for is instead solved in the component
  // via register(..., { setValueAs }), which can hand Zod `undefined`
  // directly instead of NaN.
  requested_term_count: z
    .number()
    .int("Term count must be a whole number.")
    .min(1, "Term count must be at least 1.")
    .max(60, "Term count cannot exceed 60.")
    .optional(),
  requested_term_unit: z.enum(["WEEK", "MONTH", ""]).optional(),
  customer_notes: z.string().optional(),
  declaration: z.boolean().refine((v) => v, "Confirm the information you've provided is accurate."),
});

export type LoanRequestFormValues = z.infer<typeof loanRequestSchema>;
