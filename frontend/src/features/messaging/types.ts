/** Mirrors apps/messaging/serializers.py. */

export type SMSMessageStatus =
  | "PENDING"
  | "PROCESSING"
  | "SENT"
  | "DELIVERED"
  | "FAILED"
  | "CANCELLED";

export type SMSMessageType =
  | "LOAN_OFFER_READY"
  | "OFFER_ACCEPTED_CUSTOMER"
  | "OFFER_ACCEPTED_ADMIN"
  | "LOAN_APPROVED"
  | "LOAN_DISBURSED_CUSTOMER"
  | "LOAN_DISBURSED_ADMIN"
  | "PAYMENT_RECEIVED_CUSTOMER"
  | "PAYMENT_RECEIVED_ADMIN"
  | "REPAYMENT_DUE_5_DAYS"
  | "REPAYMENT_DUE_3_DAYS"
  | "REPAYMENT_DUE_2_DAYS"
  | "REPAYMENT_DUE_1_DAY"
  | "REPAYMENT_DUE_TODAY_MORNING"
  | "REPAYMENT_DUE_TODAY_AFTERNOON"
  | "REPAYMENT_OVERDUE"
  | "LOAN_PAID_OFF_CUSTOMER"
  | "LOAN_PAID_OFF_ADMIN"
  | "MANUAL_REMINDER";

/** Mirrors SMSMessageSerializer. */
export interface SMSMessageRecord {
  id: string;
  message_type: SMSMessageType;
  recipient_phone_e164: string;
  message_body: string;
  status: SMSMessageStatus;
  customer_name: string;
  loan_number: string | null;
  attempt_count: number;
  next_attempt_at: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  failed_at: string | null;
  last_error_summary: string;
  created_at: string;
}

export type SMSMessageSummary = Record<SMSMessageStatus, number>;

export interface SMSMessageListParams {
  status?: SMSMessageStatus;
  message_type?: SMSMessageType;
  loan?: string;
}

/** Mirrors SMSSettingsSerializer — the /admin/settings Hubtel controls.
 * Times are "HH:MM:SS" strings (DRF's default TimeField rendering). */
export interface SmsSettings {
  hubtel_enabled: boolean;
  morning_reminder_time: string;
  afternoon_reminder_time: string;
  updated_at: string;
}

export type SmsSettingsPayload = Omit<SmsSettings, "updated_at">;
