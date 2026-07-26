"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getSmsMessageSummary,
  getSmsSettings,
  listSmsMessages,
  retrySmsMessage,
  sendManualReminder,
  updateSmsSettings,
} from "./api";
import type { SMSMessageListParams, SmsSettingsPayload } from "./types";

export const SMS_MESSAGES_QUERY_KEY = ["sms-messages"];

export function useSmsMessages(params: SMSMessageListParams) {
  return useQuery({
    queryKey: [...SMS_MESSAGES_QUERY_KEY, params],
    queryFn: () => listSmsMessages(params),
  });
}

export function useSmsMessageSummary() {
  return useQuery({
    queryKey: [...SMS_MESSAGES_QUERY_KEY, "summary"],
    queryFn: getSmsMessageSummary,
  });
}

export function useRetrySmsMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => retrySmsMessage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SMS_MESSAGES_QUERY_KEY });
    },
  });
}

export function useSendManualReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ installmentId, reason }: { installmentId: string; reason: string }) =>
      sendManualReminder(installmentId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SMS_MESSAGES_QUERY_KEY });
    },
  });
}

export function useSmsSettings() {
  return useQuery({
    queryKey: ["sms-settings"],
    queryFn: getSmsSettings,
  });
}

export function useUpdateSmsSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SmsSettingsPayload) => updateSmsSettings(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["sms-settings"], data);
    },
  });
}
