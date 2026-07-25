/** Mirrors apps/customers/serializers.py's MaskedCustomerProfileSerializer —
 * staff-facing only, payout account numbers are always masked server-side. */
export interface MaskedCustomerProfile {
  id: string;
  email: string;
  full_name: string;
  phone_number_e164: string;
  city: string;
  country: string;
  preferred_disbursement_method: "MOBILE_MONEY" | "BANK";
  mobile_money_network: string;
  mobile_money_number: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
  profile_completed_at: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
