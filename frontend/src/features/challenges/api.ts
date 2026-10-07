import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, type components } from "@/api";
import { checkinsKey } from "@/features/checkins";

export type Challenge = components["schemas"]["ChallengeOut"];
export type ChallengeInput = components["schemas"]["ChallengeInRequest"];
export type Pool = components["schemas"]["PoolOut"];
export type Phase = components["schemas"]["PhaseEnum"];

export const challengesKey = ["challenges"] as const;
const poolKey = [...challengesKey, "pool"] as const;
const chosenKey = (phases: string) => [...challengesKey, "chosen", phases] as const;
const challengeKey = (id: string) => [...challengesKey, "one", id] as const;

/** The crew's proposals, newest first, with votes and how full the pool is. */
export function usePool({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: poolKey,
    queryFn: () => call(api.GET("/api/v1/proposals")),
    enabled,
  });
}

/** Scheduled challenges in the given phases ("active,upcoming"). */
export function useChosenChallenges(phases: Phase[], { enabled = true } = {}) {
  const phase = phases.join(",");
  return useQuery({
    queryKey: chosenKey(phase),
    queryFn: () => call(api.GET("/api/v1/challenges", { params: { query: { phase } } })),
    enabled,
  });
}

export function useChallenge(id: string) {
  return useQuery({
    queryKey: challengeKey(id),
    queryFn: () =>
      call(
        api.GET("/api/v1/challenges/{challenge_id}", { params: { path: { challenge_id: id } } }),
      ),
  });
}

/** Everything about challenges changes together: refetch it all after any write. */
function useInvalidate() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: challengesKey });
}

const path = (id: string) => ({ params: { path: { challenge_id: id } } });

export function useProposeChallenge() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: ChallengeInput) => call(api.POST("/api/v1/challenges", { body })),
    onSuccess: invalidate,
  });
}

export function useEditChallenge(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: ChallengeInput) =>
      call(api.PUT("/api/v1/challenges/{challenge_id}", { ...path(id), body })),
    onSuccess: invalidate,
  });
}

export function useWithdrawChallenge() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => call(api.DELETE("/api/v1/challenges/{challenge_id}", path(id))),
    onSuccess: invalidate,
  });
}

/** The creator changes who takes part while the challenge is a proposal. */
export function useSetParticipants(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (participantIds: string[]) =>
      call(
        api.PUT("/api/v1/challenges/{challenge_id}/participants", {
          ...path(id),
          body: { participant_ids: participantIds },
        }),
      ),
    onSuccess: invalidate,
  });
}

/** Vote for a proposal or take the vote back. The pool shows the change at once. */
export function useVote() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, vote }: { id: string; vote: boolean }) =>
      vote
        ? call(api.PUT("/api/v1/challenges/{challenge_id}/vote", path(id)))
        : call(api.DELETE("/api/v1/challenges/{challenge_id}/vote", path(id))),
    onMutate: async ({ id, vote }) => {
      await queryClient.cancelQueries({ queryKey: poolKey });
      const previous = queryClient.getQueryData<Pool>(poolKey);
      if (previous) {
        queryClient.setQueryData<Pool>(poolKey, {
          ...previous,
          proposals: previous.proposals.map((p) =>
            p.id === id && p.my_vote !== vote
              ? { ...p, my_vote: vote, vote_count: p.vote_count + (vote ? 1 : -1) }
              : p,
          ),
        });
      }
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(poolKey, context.previous);
    },
    onSettled: invalidate,
  });
}

/** Admin: pick when a proposal starts, or move a scheduled one before it starts. */
export function useSchedule(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (periodStart: string) =>
      call(
        api.PUT("/api/v1/challenges/{challenge_id}/schedule", {
          ...path(id),
          body: { period_start: periodStart },
        }),
      ),
    onSuccess: (detail) => {
      queryClient.setQueryData(challengeKey(id), detail);
      void queryClient.invalidateQueries({ queryKey: challengesKey });
      void queryClient.invalidateQueries({ queryKey: checkinsKey }); // its windows moved too
    },
  });
}

/** Admin: put a scheduled challenge back in the pool before it starts. */
export function useUnschedule(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.DELETE("/api/v1/challenges/{challenge_id}/schedule", path(id))),
    onSuccess: (detail) => {
      queryClient.setQueryData(challengeKey(id), detail);
      void queryClient.invalidateQueries({ queryKey: challengesKey });
    },
  });
}

/**
 * Opt out before the start or leave a running challenge. Either way it is gone for the member
 * afterwards, so every list (and today's check-ins) is fetched again.
 */
export function useLeave(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => call(api.DELETE("/api/v1/challenges/{challenge_id}/participation", path(id))),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: challengeKey(id) });
      void queryClient.invalidateQueries();
    },
  });
}
