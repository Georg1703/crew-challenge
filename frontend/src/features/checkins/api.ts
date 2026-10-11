import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";
import { useCallback } from "react";

import { api, call, type components } from "@/api";
import type { ProofSubject } from "@/features/proofs";

export type Today = components["schemas"]["TodayOut"];
export type TodayChallenge = components["schemas"]["TodayChallengeOut"];
export type Board = components["schemas"]["BoardOut"];
export type JournalEntry = components["schemas"]["JournalEntryOut"];
export type JournalPage = components["schemas"]["JournalPageOut"];
export type MemberProgress = components["schemas"]["MemberProgressOut"];
export type Window = components["schemas"]["WindowOut"];

export const checkinsKey = ["checkins"] as const;
const todayKey = [...checkinsKey, "today"] as const;
const boardKey = (id: string, month: string) => [...checkinsKey, "board", id, month] as const;
const journalKey = [...checkinsKey, "journal"] as const;
const cardKey = (id: string) => [...checkinsKey, "card", id] as const;
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

const JOURNAL_REFRESH_MS = 60_000;

/**
 * The crew's journal: one card per post, each as it was posted, latest first, 30 a page.
 * Refreshed when the app comes back to the front and every minute while it is open (a post
 * refreshes it too: it lives under the check-ins key).
 */
export function useJournal() {
  return useInfiniteQuery({
    queryKey: journalKey,
    queryFn: ({ pageParam }) =>
      call(
        api.GET("/api/v1/journal", { params: { query: pageParam ? { cursor: pageParam } : {} } }),
      ),
    initialPageParam: "",
    getNextPageParam: (page) => page.next ?? undefined,
    refetchInterval: JOURNAL_REFRESH_MS,
  });
}

type JournalPages = InfiniteData<JournalPage, string>;

/** One card (its own page): from the cached journal at once when it is there, then fresh. */
export function useJournalCard(id: string) {
  const client = useQueryClient();
  return useQuery({
    queryKey: cardKey(id),
    queryFn: () =>
      call(api.GET("/api/v1/journal/{entry_id}", { params: { path: { entry_id: id } } })),
    initialData: () =>
      client
        .getQueryData<JournalPages>(journalKey)
        ?.pages.flatMap((page) => page.results)
        .find((entry) => entry.id === id),
    initialDataUpdatedAt: () => client.getQueryState(journalKey)?.dataUpdatedAt,
  });
}

/** Put a card's new reactions into the cached journal and card (the reactions feature calls it). */
export function usePatchJournalReactions() {
  const client = useQueryClient();
  return useCallback(
    (id: string, reactions: JournalEntry["reactions"]) => {
      void client.cancelQueries({ queryKey: journalKey }); // a refresh in flight would undo it
      client.setQueryData<JournalPages>(journalKey, (data) =>
        data
          ? {
              ...data,
              pages: data.pages.map((page) => ({
                ...page,
                results: page.results.map((entry) =>
                  entry.id === id ? { ...entry, reactions } : entry,
                ),
              })),
            }
          : data,
      );
      client.setQueryData<JournalEntry>(cardKey(id), (entry) => entry && { ...entry, reactions });
    },
    [client],
  );
}

/** A card's comments were read: its unread mark goes, in the cached journal and card. */
export function useMarkJournalCardRead() {
  const client = useQueryClient();
  return useCallback(
    (id: string) => {
      const read = (entry: JournalEntry) =>
        entry.id === id ? { ...entry, comments: { ...entry.comments, unread: 0 } } : entry;
      client.setQueryData<JournalPages>(journalKey, (data) =>
        data
          ? {
              ...data,
              pages: data.pages.map((page) => ({ ...page, results: page.results.map(read) })),
            }
          : data,
      );
      client.setQueryData<JournalEntry>(cardKey(id), (entry) => entry && read(entry));
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

/**
 * Post: today's check-in, a "+N", or files added later, with today's uploaded draft files.
 * Optimistic: the card fills at once and rolls back on error.
 */
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

/** Undo today's latest post for a challenge, with its files. */
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

/**
 * Today's check-in as a proof subject for the upload engine: start a draft file on it, or resume
 * this file's unfinished upload on it (until midnight). `key` groups this phone's uploads under
 * the challenge's card for that day.
 */
export function checkInProofs(challengeId: string, day: string): ProofSubject {
  return {
    key: `check-in:${challengeId}:${day}`,
    start: (body) =>
      call(
        api.POST("/api/v1/challenges/{challenge_id}/check-ins/{day}/proofs", {
          params: { path: { challenge_id: challengeId, day } },
          body,
        }),
      ),
    resume: (fingerprint) =>
      call(
        api.GET("/api/v1/challenges/{challenge_id}/check-ins/proofs/resume", {
          params: { path: { challenge_id: challengeId }, query: { fingerprint } },
        }),
      ),
  };
}
