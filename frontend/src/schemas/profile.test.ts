import { describe, expect, it } from "vitest";

import { profileSchema } from "./profile";

const BASE = {
  first_name: "Ama",
  last_name: "Owusu",
  phone_number_e164: "0241234567",
  declaration: true,
};

describe("profileSchema", () => {
  it("requires a payout method", () => {
    const result = profileSchema.safeParse({ ...BASE, preferred_disbursement_method: undefined });

    expect(result.success).toBe(false);
  });

  it("requires mobile money network and number when method is MOBILE_MONEY", () => {
    const result = profileSchema.safeParse({
      ...BASE,
      preferred_disbursement_method: "MOBILE_MONEY",
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path.join("."));
      expect(paths).toContain("mobile_money_network");
      expect(paths).toContain("mobile_money_number");
    }
  });

  it("accepts a complete mobile money profile", () => {
    const result = profileSchema.safeParse({
      ...BASE,
      preferred_disbursement_method: "MOBILE_MONEY",
      mobile_money_network: "MTN",
      mobile_money_number: "0241234567",
    });

    expect(result.success).toBe(true);
  });

  it("requires bank fields when method is BANK, not mobile money fields", () => {
    const result = profileSchema.safeParse({
      ...BASE,
      preferred_disbursement_method: "BANK",
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path.join("."));
      expect(paths).toContain("bank_name");
      expect(paths).toContain("bank_account_name");
      expect(paths).toContain("bank_account_number");
      expect(paths).not.toContain("mobile_money_network");
    }
  });

  it("accepts a complete bank profile", () => {
    const result = profileSchema.safeParse({
      ...BASE,
      preferred_disbursement_method: "BANK",
      bank_name: "GCB Bank",
      bank_account_name: "Ama Owusu",
      bank_account_number: "1234567890",
    });

    expect(result.success).toBe(true);
  });

  it("requires first and last name", () => {
    const result = profileSchema.safeParse({
      ...BASE,
      first_name: "",
      last_name: "",
      preferred_disbursement_method: "MOBILE_MONEY",
      mobile_money_network: "MTN",
      mobile_money_number: "0241234567",
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path.join("."));
      expect(paths).toContain("first_name");
      expect(paths).toContain("last_name");
    }
  });

  it("rejects an unchecked declaration even when every other field is valid", () => {
    const result = profileSchema.safeParse({
      first_name: "Ama",
      last_name: "Owusu",
      phone_number_e164: "0241234567",
      preferred_disbursement_method: "MOBILE_MONEY",
      mobile_money_network: "MTN",
      mobile_money_number: "0241234567",
      declaration: false,
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path.join("."));
      expect(paths).toContain("declaration");
    }
  });
});
