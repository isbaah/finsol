/** GHS is always shown as the currency code, never a bare symbol
 * (docs/PRODUCT_ASSUMPTIONS.md Section 1) — `currencyDisplay: "code"`
 * guarantees "GHS 1,234.56" regardless of locale defaults. */
const CURRENCY_FORMATTER = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  currencyDisplay: "code",
});

export function formatGHS(amount: string | number): string {
  return CURRENCY_FORMATTER.format(Number(amount));
}

/** Unambiguous date display (master prompt Section 13: "24 Sep 2026", not
 * a locale-ambiguous numeric format like 09/24/26). */
const DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function formatDate(isoDate: string): string {
  // Parsed as a plain calendar date (no time/timezone component) so it
  // never shifts a day depending on the viewer's timezone. Only for
  // DRF DateField values (due dates, first_due_date, offer_expiry_date) —
  // a full ISO datetime string here (e.g. "2026-09-01T12:00:00Z") makes
  // `day` parse as NaN. Use formatDateTime() for DateTimeField values.
  const [year, month, day] = isoDate.split("-").map(Number);
  return DATE_FORMATTER.format(new Date(year, month - 1, day));
}

/** For DRF DateTimeField values (submitted_at, sent_at, created_at, ...) —
 * a full ISO instant, not a plain calendar date. Displayed date-only, same
 * "24 Sep 2026" format as formatDate(), since none of these fields' UI
 * needs time-of-day precision. */
export function formatDateTime(isoDateTime: string): string {
  return DATE_FORMATTER.format(new Date(isoDateTime));
}
