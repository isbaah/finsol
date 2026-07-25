"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getSmsMessageSummary, listSmsMessages, retrySmsMessage, sendManualReminder } from "./api";
import type { SMSMessageListParams } from "./types";

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
