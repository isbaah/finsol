"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ME_QUERY_KEY } from "@/features/me/use-me";

import { getMyProfile, saveMyProfile } from "./api";

export const PROFILE_QUERY_KEY = ["profile"];

export function useMyProfile() {
  return useQuery({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: getMyProfile,
    retry: false,
  });
}

export function useSaveProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveMyProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY });
      // profile_completed on /api/v1/me/ changes the instant the profile
      // is saved — refresh it so ProfileGuard stops redirecting.
      queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
    },
  });
}
