import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, type components } from "@/api";

import { currentSubscription } from "./push";

export type Notification = components["schemas"]["NotificationOut"];
export type News = components["schemas"]["NewsOut"];

/** How often the badge and the list ask for news (and when the app comes back). */
const NEWS_MS = 60_000;

export const newsKey = ["notifications"] as const;
const pushKeyKey = ["push", "key"] as const;

/** My news in this crew, latest first, and how many are unread (the Crew tab's badge). */
export function useNews(enabled = true) {
  return useQuery({
    queryKey: newsKey,
    queryFn: () => call(api.GET("/api/v1/notifications")),
    refetchInterval: NEWS_MS,
    enabled,
  });
}

/** I have seen my news: the badge clears; the rows keep their dots until the next refresh. */
export function useMarkNewsRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.PUT("/api/v1/notifications/read")),
    onSuccess: () => client.setQueryData<News>(newsKey, (news) => news && { ...news, unread: 0 }),
  });
}

/** The server's push key; empty when push is off there. Asked once. */
export function usePushKey(enabled = true) {
  return useQuery({
    queryKey: pushKeyKey,
    queryFn: () => call(api.GET("/api/v1/push/key")).then((key) => key.public_key),
    staleTime: Infinity,
    enabled,
  });
}

type Subscription = { endpoint: string; keys: { p256dh: string; auth: string } };

export function useSubscribePush() {
  return useMutation({
    mutationFn: (body: Subscription) => call(api.PUT("/api/v1/push/subscriptions", { body })),
  });
}

export function useUnsubscribePush() {
  return useMutation({
    mutationFn: (endpoint: string) =>
      call(api.DELETE("/api/v1/push/subscriptions", { params: { query: { endpoint } } })),
  });
}

/**
 * Tell the server this browser's current subscription again (browsers renew endpoints; the
 * server upserts). Call on app start; nothing without permission or a subscription.
 */
export async function renewPush(): Promise<void> {
  try {
    const current = await currentSubscription();
    if (current) await call(api.PUT("/api/v1/push/subscriptions", { body: current }));
  } catch {
    // Not critical: the next start tries again.
  }
}
