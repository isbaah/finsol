import { z } from "zod";

export const agreementAcceptanceSchema = z.object({
  typed_legal_name: z
    .string()
    .trim()
    .min(2, "Enter your full legal name as it should appear on the agreement."),
  declaration_accepted: z.boolean().refine((v) => v, {
    message: "You must confirm the acceptance declaration.",
  }),
});

export type AgreementAcceptanceFormValues = z.infer<typeof agreementAcceptanceSchema>;
