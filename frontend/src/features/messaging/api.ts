import { apiFetch } from "@/lib/api-client";
import type { PaginatedResponse } from "@/features/loan-requests/types";

import type {
  SMSMessageListParams,
  SMSMessageRecord,
  SMSMessageSummary,
  SmsSettings,
  SmsSettingsPayload,
} from "./types";

export function listSmsMessages(params: SMSMessageListParams = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.message_type) query.set("message_type", params.message_type);
  if (params.loan) query.set("loan", params.loan);
  const qs = query.toString();
  return apiFetch<PaginatedResponse<SMSMessageRecord>>(
    `/api/v1/admin/sms-messages/${qs ? `?${qs}` : ""}`,
  );
}

export function getSmsMessageSummary() {
  return apiFetch<SMSMessageSummary>("/api/v1/admin/sms-messages/summary/");
}

export function retrySmsMessage(id: string) {
  return apiFetch<SMSMessageRecord>(`/api/v1/admin/sms-messages/${id}/retry/`, { method: "POST" });
}

export function sendManualReminder(installmentId: string, reason: string) {
  return apiFetch<SMSMessageRecord>(`/api/v1/admin/installments/${installmentId}/manual-reminder/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function getSmsSettings() {
  return apiFetch<SmsSettings>("/api/v1/admin/sms-settings/");
}

export function updateSmsSettings(payload: SmsSettingsPayload) {
  return apiFetch<SmsSettings>("/api/v1/admin/sms-settings/", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
