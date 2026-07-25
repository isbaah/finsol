/** Mirrors apps/customers/serializers.py's CustomerProfileSerializer. */

export type DisbursementMethod = "MOBILE_MONEY" | "BANK";
export type MobileMoneyNetwork = "MTN" | "TELECEL" | "AIRTELTIGO" | "OTHER";

export interface CustomerProfile {
  id: string;
  first_name: string;
  last_name: string;
  phone_number_e164: string;
  phone_country_code: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  country: string;
  preferred_disbursement_method: DisbursementMethod;
  mobile_money_network: MobileMoneyNetwork | "";
  mobile_money_number: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
  profile_completed_at: string | null;
  created_at: string;
  updated_at: string;
}

/** PUT /api/v1/profile/ body — field names match the API 1:1 (see
 * schemas/profile.ts for why, unlike the auth forms' camelCase). */
export interface ProfilePayload {
  first_name: string;
  last_name: string;
  phone_number_e164: string;
  address_line_1?: string;
  address_line_2?: string;
  city?: string;
  preferred_disbursement_method: DisbursementMethod;
  // A loose string, not MobileMoneyNetwork | "" — see schemas/profile.ts for
  // why the form field itself can't be strictly typed to the enum. The
  // backend is the final authority on valid values regardless.
  mobile_money_network?: string;
  mobile_money_number?: string;
  bank_name?: string;
  bank_account_name?: string;
  bank_account_number?: string;
}
