import { useMutation, useQuery } from "@tanstack/react-query";

import { api, call } from "@/api";

export const crewKey = ["crew"] as const;

export function useCrew({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: crewKey,
    queryFn: () => call(api.GET("/api/v1/crew")),
    enabled,
  });
}

export function useCreateInvite() {
  return useMutation({ mutationFn: () => call(api.POST("/api/v1/crew/invites")) });
}
