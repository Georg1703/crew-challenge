import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, type components } from "@/api";

export type Today = components["schemas"]["TodayOut"];
export type TodayChallenge = components["schemas"]["TodayChallengeOut"];
export type Board = components["schemas"]["BoardOut"];

export const checkinsKey = ["checkins"] as const;
const todayKey = [...checkinsKey, "today"] as const;
const boardKey = (id: string, month: string) => [...checkinsKey, "board", id, month] as const;

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

/** What a check-in will most likely look like, so the card changes before the server answers. */
export function predict(card: TodayChallenge, amount: number | null): TodayChallenge {
  const total = card.measure === "quantity" ? (card.total ?? 0) + (amount ?? 0) : null;
  const target = card.target_scope === "per_check_in" ? card.target_value : null;
  const done = total === null || (target ? total >= target : total > 0);
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
