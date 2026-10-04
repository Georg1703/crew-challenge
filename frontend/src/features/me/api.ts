import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/api";
import { meKey } from "@/features/auth";
import { crewKey } from "@/features/crew";

export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { display_name?: string; preferred_language?: "ro" | "en" }) =>
      call(api.PATCH("/api/v1/me", { body })),
    onSuccess: (me) => {
      queryClient.setQueryData(meKey, me);
      void queryClient.invalidateQueries({ queryKey: crewKey });
    },
  });
}

/** Act in another of the user's crews. Everything cached belonged to the previous crew. */
export function useSwitchCrew() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (crewId: string) => call(api.PUT("/api/v1/me/crew", { body: { crew_id: crewId } })),
    onSuccess: (me) => {
      queryClient.clear();
      queryClient.setQueryData(meKey, me);
    },
  });
}
