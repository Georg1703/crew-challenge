import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";
import { useCallback } from "react";

import { api, call, isApiError, type components } from "@/api";

export type Today = components["schemas"]["TodayOut"];
export type TodayChallenge = components["schemas"]["TodayChallengeOut"];
export type Board = components["schemas"]["BoardOut"];
export type Proof = components["schemas"]["ProofOut"];
export type ProofUpload = components["schemas"]["ProofUploadOut"];
export type ProofStart = components["schemas"]["ProofStartInRequest"];
export type FeedItem = components["schemas"]["FeedItemOut"];
export type MemberProgress = components["schemas"]["MemberProgressOut"];
export type Window = components["schemas"]["WindowOut"];

export const checkinsKey = ["checkins"] as const;
const todayKey = [...checkinsKey, "today"] as const;
const boardKey = (id: string, month: string) => [...checkinsKey, "board", id, month] as const;
const feedKey = [...checkinsKey, "feed"] as const;
const dayKey = (id: string, day: string) => [...checkinsKey, "day", id, day] as const;
const memberKey = (id: string) => [...checkinsKey, "member", id] as const;
type WindowsQuery = { start?: string; until?: string };
const windowsKey = (id: string, query: WindowsQuery) =>
  [...checkinsKey, "windows", id, query] as const;

/** A member's month (this month) on the challenges you can see: streaks, days and proofs by day. */
export function useMemberProgress(id: string) {
  return useQuery({
    queryKey: memberKey(id),
    queryFn: () =>
      call(
        api.GET("/api/v1/members/{member_id}/progress", { params: { path: { member_id: id } } }),
      ),
  });
}

/** My challenges today and the crew's progress. Refetched when the app comes back to the front. */
export function useToday({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: todayKey,
    queryFn: () => call(api.GET("/api/v1/today")),
    enabled,
  });
}

export function useBoard(id: string, month: string) {
  return useQuery({
    queryKey: boardKey(id, month),
    queryFn: () =>
      call(
        api.GET("/api/v1/challenges/{challenge_id}/board", {
          params: { path: { challenge_id: id }, query: { month } },
        }),
      ),
  });
}

/**
 * A challenge's weeks, months or whole period: what each asks for and, for a participant, how it
 * stands. `start`: as if scheduled from that day; `until`: as if you left that day.
 */
export function useWindows(id: string, query: WindowsQuery = {}, { enabled = true } = {}) {
  return useQuery({
    queryKey: windowsKey(id, query),
    queryFn: () =>
      call(
        api.GET("/api/v1/challenges/{challenge_id}/windows", {
          params: { path: { challenge_id: id }, query },
        }),
      ),
    enabled,
  });
}

const FEED_REFRESH_MS = 60_000;

/**
 * The crew's check-ins with their proofs, latest activity first, 30 a page. Refreshed when the app
 * comes back to the front and every minute while it is open (a finished upload refreshes it too:
 * it lives under the check-ins key).
 */
export function useFeed() {
  return useInfiniteQuery({
    queryKey: feedKey,
    queryFn: ({ pageParam }) =>
      call(api.GET("/api/v1/feed", { params: { query: pageParam ? { cursor: pageParam } : {} } })),
    initialPageParam: "",
    getNextPageParam: (page) => page.next ?? undefined,
    refetchInterval: FEED_REFRESH_MS,
  });
}

type FeedPages = InfiniteData<components["schemas"]["PaginatedFeedItemOutList"], string>;

/** Put a check-in's new reactions into the cached feed (the reactions feature calls it). */
export function usePatchFeedReactions() {
  const client = useQueryClient();
  return useCallback(
    (id: string, reactions: FeedItem["reactions"]) => {
      void client.cancelQueries({ queryKey: feedKey }); // a refresh in flight would undo it
      client.setQueryData<FeedPages>(feedKey, (data) =>
        data
          ? {
              ...data,
              pages: data.pages.map((page) => ({
                ...page,
                results: page.results.map((item) =>
                  item.id === id ? { ...item, reactions } : item,
                ),
              })),
            }
          : data,
      );
    },
    [client],
  );
}

/** Everyone's state, total and proofs on one day of a challenge (the day sheet). */
export function useDaySheet(id: string, day: string | null) {
  return useQuery({
    queryKey: dayKey(id, day ?? ""),
    queryFn: () =>
      call(
        api.GET("/api/v1/challenges/{challenge_id}/days/{day}", {
          params: { path: { challenge_id: id, day: day ?? "" } },
        }),
      ),
    enabled: day !== null,
  });
}

/** What a check-in will most likely look like, so the card changes before the server answers. */
export function predict(card: TodayChallenge, amount: number | null): TodayChallenge {
  const total = card.measure === "quantity" ? (card.total ?? 0) + (amount ?? 0) : null;
  const done = total === null || (card.day_min ? total >= card.day_min : total > 0);
  const state = done ? "done" : "partial";
  return {
    ...card,
    total,
    state,
    settled: card.settled === null ? null : done || card.settled,
    week: card.week.map((day) =>
      day.state === "todo" || day.state === "open" || day.state === "partial"
        ? { ...day, state }
        : day,
    ),
  };
}

function useReplaceCard() {
  const queryClient = useQueryClient();
  return (card: TodayChallenge) =>
    queryClient.setQueryData<Today>(todayKey, (today) =>
      today
        ? { ...today, challenges: today.challenges.map((c) => (c.id === card.id ? card : c)) }
        : today,
    );
}

/** Check in for today. Optimistic: the card fills at once and rolls back on error. */
export function useCheckIn() {
  const queryClient = useQueryClient();
  const replace = useReplaceCard();
  return useMutation({
    mutationFn: ({
      card,
      day,
      amount,
    }: {
      card: TodayChallenge;
      day: string;
      amount: number | null;
    }) =>
      call(
        api.POST("/api/v1/challenges/{challenge_id}/check-ins", {
          params: { path: { challenge_id: card.id } },
          body: { day, amount: amount === null ? null : String(amount) },
        }),
      ),
    onMutate: async ({ card, amount }) => {
      await queryClient.cancelQueries({ queryKey: todayKey });
      const previous = queryClient.getQueryData<Today>(todayKey);
      replace(predict(card, amount));
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(todayKey, context.previous);
    },
    onSuccess: (card) => replace(card),
    onSettled: () => queryClient.invalidateQueries({ queryKey: checkinsKey }),
  });
}

/** Undo today's last entry for a challenge. */
export function useUndoCheckIn() {
  const queryClient = useQueryClient();
  const replace = useReplaceCard();
  return useMutation({
    mutationFn: ({ id, day }: { id: string; day: string }) =>
      call(
        api.DELETE("/api/v1/challenges/{challenge_id}/check-ins/{day}/last", {
          params: { path: { challenge_id: id, day } },
        }),
      ),
    onSuccess: (card) => card && replace(card),
    onSettled: () => queryClient.invalidateQueries({ queryKey: checkinsKey }),
  });
}

/** Proof calls for the upload engine, which runs outside React (see uploads/engine.ts). */
export const proofApi = {
  start: (challengeId: string, day: string, body: ProofStart) =>
    call(
      api.POST("/api/v1/challenges/{challenge_id}/check-ins/{day}/proofs", {
        params: { path: { challenge_id: challengeId, day } },
        body,
      }),
    ),
  /** My unfinished video upload for this file, or null. */
  resume: async (fingerprint: string): Promise<ProofUpload | null> => {
    try {
      return await call(api.GET("/api/v1/proofs/resume", { params: { query: { fingerprint } } }));
    } catch (error) {
      if (isApiError(error) && error.status === 404) return null;
      throw error;
    }
  },
  signPart: async (proofId: string, number: number) => {
    const signed = await call(
      api.POST("/api/v1/proofs/{proof_id}/parts", {
        params: { path: { proof_id: proofId } },
        body: { numbers: [number] },
      }),
    );
    const part = signed.parts[0];
    if (!part) throw new Error(`No URL for part ${number}.`);
    return part.url;
  },
  reportPart: (proofId: string, number: number, etag: string) =>
    call(
      api.PUT("/api/v1/proofs/{proof_id}/parts/{number}", {
        params: { path: { proof_id: proofId, number } },
        body: { etag },
      }),
    ),
  complete: (proofId: string) =>
    call(
      api.POST("/api/v1/proofs/{proof_id}/complete", { params: { path: { proof_id: proofId } } }),
    ),
  remove: (proofId: string) =>
    call(api.DELETE("/api/v1/proofs/{proof_id}", { params: { path: { proof_id: proofId } } })),
};

const MEDIA_SESSION_MS = 12 * 60 * 60 * 1000; // the cookies last 24 h; renew at half

/**
 * The CloudFront cookies that let this browser load the crew's photos and videos (production).
 * Asked again for another crew, and when the app comes back after half their life. Locally a
 * no-op on the server.
 */
export function useMediaSession(memberId: string | undefined) {
  useQuery({
    queryKey: ["media", "session", memberId],
    queryFn: () => call(api.POST("/api/v1/media/session")),
    enabled: Boolean(memberId),
    staleTime: MEDIA_SESSION_MS,
    refetchInterval: MEDIA_SESSION_MS,
  });
}
