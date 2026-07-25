import { z } from "zod";

const MOBILE_MONEY_NETWORKS = ["MTN", "TELECEL", "AIRTELTIGO", "OTHER"] as const;

// Field names match the backend serializer 1:1 (snake_case) rather than the
// auth forms' camelCase convention — this form's fields map straight onto
// apps/customers/serializers.py's CustomerProfileSerializer, so keeping the
// names identical lets applyDrfErrors (lib/drf-errors.ts) attach a server
// validation error straight to the right RHF field with no translation
// table to keep in sync (and no risk of it drifting out of sync).
export const profileSchema = z
  .object({
    first_name: z.string().min(1, "First name is required."),
    last_name: z.string().min(1, "Last name is required."),
    phone_number_e164: z.string().min(1, "Phone number is required."),
    address_line_1: z.string().optional(),
    address_line_2: z.string().optional(),
    city: z.string().optional(),
    preferred_disbursement_method: z.enum(["MOBILE_MONEY", "BANK"], {
      message: "Choose a payout method.",
    }),
    // A loose string, not z.enum(...).optional(): the network <select> stays
    // mounted (and registered with react-hook-form) even while the BANK
    // branch is shown, and its unselected placeholder option's value is ""
    // — not undefined — which z.enum(...).optional() rejects outright,
    // blocking submission of an otherwise-valid bank profile. Real
    // membership is checked below, only when it's actually relevant.
    mobile_money_network: z.string().optional(),
    mobile_money_number: z.string().optional(),
    bank_name: z.string().optional(),
    bank_account_name: z.string().optional(),
    bank_account_number: z.string().optional(),
    // Optional at the base-shape level for the same reason as
    // schemas/auth.ts's signup declaration: Zod skips superRefine/refine
    // entirely if base shape validation fails first.
    declaration: z.boolean().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.preferred_disbursement_method === "MOBILE_MONEY") {
      if (!data.mobile_money_network) {
        ctx.addIssue({
          code: "custom",
          message: "Select a network.",
          path: ["mobile_money_network"],
        });
      } else if (
        !(MOBILE_MONEY_NETWORKS as readonly string[]).includes(data.mobile_money_network)
      ) {
        ctx.addIssue({
          code: "custom",
          message: "Select a valid network.",
          path: ["mobile_money_network"],
        });
      }
      if (!data.mobile_money_number) {
        ctx.addIssue({
          code: "custom",
          message: "Mobile money number is required.",
          path: ["mobile_money_number"],
        });
      }
    }
    if (data.preferred_disbursement_method === "BANK") {
      if (!data.bank_name) {
        ctx.addIssue({ code: "custom", message: "Bank name is required.", path: ["bank_name"] });
      }
      if (!data.bank_account_name) {
        ctx.addIssue({
          code: "custom",
          message: "Account name is required.",
          path: ["bank_account_name"],
        });
      }
      if (!data.bank_account_number) {
        ctx.addIssue({
          code: "custom",
          message: "Account number is required.",
          path: ["bank_account_number"],
        });
      }
    }
    if (data.declaration !== true) {
      ctx.addIssue({
        code: "custom",
        message: "You must confirm the information is accurate.",
        path: ["declaration"],
      });
    }
  });

export type ProfileFormValues = z.infer<typeof profileSchema>;
