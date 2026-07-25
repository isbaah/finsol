import { describe, expect, it } from "vitest";

import { amortizationPreviewSchema } from "./amortization";

const VALID = {
  principal: "10000.00",
  interest_rate_percent: "12.00",
  term_count: 6,
  term_unit: "MONTH" as const,
  first_due_date: "2026-09-01",
};

describe("amortizationPreviewSchema", () => {
  it("accepts a fully valid input", () => {
    expect(amortizationPreviewSchema.safeParse(VALID).success).toBe(true);
  });

  it("rejects a zero or negative principal", () => {
    expect(amortizationPreviewSchema.safeParse({ ...VALID, principal: "0" }).success).toBe(false);
    expect(amortizationPreviewSchema.safeParse({ ...VALID, principal: "-5" }).success).toBe(false);
  });

  it("rejects a negative interest rate", () => {
    const result = amortizationPreviewSchema.safeParse({
      ...VALID,
      interest_rate_percent: "-1",
    });
    expect(result.success).toBe(false);
  });

  it("rejects a term count outside 1-60", () => {
    expect(amortizationPreviewSchema.safeParse({ ...VALID, term_count: 0 }).success).toBe(false);
    expect(amortizationPreviewSchema.safeParse({ ...VALID, term_count: 61 }).success).toBe(false);
  });

  it("rejects an unsupported term unit", () => {
    const result = amortizationPreviewSchema.safeParse({ ...VALID, term_unit: "DAY" });
    expect(result.success).toBe(false);
  });
});
