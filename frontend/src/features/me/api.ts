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
