import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, isApiError, type Me } from "@/api";

export const meKey = ["me"] as const;

/** The logged-in user, or null when there is no session. */
export function useMe() {
  return useQuery({
    queryKey: meKey,
    queryFn: async (): Promise<Me | null> => {
      try {
        return await call(api.GET("/api/v1/me"));
      } catch (error) {
        if (isApiError(error) && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { username: string; password: string }) =>
      call(api.POST("/api/v1/auth/login", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: meKey }),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.POST("/api/v1/auth/logout")),
    onSettled: () => {
      queryClient.clear();
      queryClient.setQueryData(meKey, null);
    },
  });
}

export function useInvitePreview(code: string) {
  return useQuery({
    queryKey: ["invite", code],
    queryFn: () => call(api.GET("/api/v1/invites/{code}", { params: { path: { code } } })),
    retry: false,
  });
}

export function useAcceptInvite(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { username: string; password: string; display_name: string }) =>
      call(api.POST("/api/v1/invites/{code}/accept", { params: { path: { code } }, body })),
    onSuccess: (me) => queryClient.setQueryData(meKey, me),
  });
}

/** A logged-in user joins the invite's crew with the account they already have. */
export function useJoinWithAccount(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { display_name: string }) =>
      call(api.POST("/api/v1/invites/{code}/join", { params: { path: { code } }, body })),
    onSuccess: (me) => {
      // Everything cached belonged to the previous crew.
      queryClient.clear();
      queryClient.setQueryData(meKey, me);
    },
  });
}
