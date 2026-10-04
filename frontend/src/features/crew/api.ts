import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, type PendingInvite } from "@/api";

export const crewKey = ["crew"] as const;
export const pendingInvitesKey = ["crew", "invites"] as const;

export function useCrew({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: crewKey,
    queryFn: () => call(api.GET("/api/v1/crew")),
    enabled,
  });
}

/** Admins only: invites nobody has used yet, newest first. */
export function usePendingInvites({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: pendingInvitesKey,
    queryFn: () => call(api.GET("/api/v1/crew/invites")),
    enabled,
  });
}

export function useCreateInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/crew/invites")),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: pendingInvitesKey }),
  });
}

/** Cancels an invite. The row disappears at once and comes back if the server says no. */
export function useRevokeInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invite: PendingInvite) =>
      call(
        api.DELETE("/api/v1/crew/invites/{invite_id}", {
          params: { path: { invite_id: invite.id } },
        }),
      ),
    onMutate: async (invite) => {
      await queryClient.cancelQueries({ queryKey: pendingInvitesKey });
      const previous = queryClient.getQueryData<PendingInvite[]>(pendingInvitesKey);
      queryClient.setQueryData<PendingInvite[]>(pendingInvitesKey, (current) =>
        current?.filter((item) => item.id !== invite.id),
      );
      return { previous };
    },
    onError: (_error, _invite, context) => {
      if (context?.previous) queryClient.setQueryData(pendingInvitesKey, context.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: pendingInvitesKey }),
  });
}
