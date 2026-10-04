import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, type components } from "@/api";

export type Round = components["schemas"]["RoundOut"];
export type Proposal = components["schemas"]["ProposalOut"];
export type Challenge = components["schemas"]["ChallengeOut"];
export type ChallengeDetail = components["schemas"]["ChallengeDetailOut"];
export type ChallengeInput = components["schemas"]["ChallengeInRequest"];
export type Phase = components["schemas"]["PhaseEnum"];

export const challengesKey = ["challenges"] as const;
const currentRoundKey = [...challengesKey, "round", "current"] as const;
const chosenKey = (phases: string) => [...challengesKey, "chosen", phases] as const;
const challengeKey = (id: string) => [...challengesKey, "one", id] as const;

/** The round people propose and vote in now. */
export function useCurrentRound({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: currentRoundKey,
    queryFn: () => call(api.GET("/api/v1/rounds/current")),
    enabled,
  });
}

/** Chosen challenges in the given phases ("active,upcoming"). */
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
      call(
        api.PUT("/api/v1/challenges/{challenge_id}", {
          params: { path: { challenge_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useWithdrawChallenge() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      call(
        api.DELETE("/api/v1/challenges/{challenge_id}", { params: { path: { challenge_id: id } } }),
      ),
    onSuccess: invalidate,
  });
}

export function useRepropose() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      call(
        api.POST("/api/v1/challenges/{challenge_id}/repropose", {
          params: { path: { challenge_id: id } },
        }),
      ),
    onSuccess: invalidate,
  });
}

/** Vote for a proposal; the round comes back with the new counts. Optimistic `my_vote`. */
export function useVote() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ roundId, challengeId }: { roundId: string; challengeId: string | null }) =>
      challengeId
        ? call(
            api.PUT("/api/v1/rounds/{round_id}/vote", {
              params: { path: { round_id: roundId } },
              body: { challenge_id: challengeId },
            }),
          )
        : call(
            api.DELETE("/api/v1/rounds/{round_id}/vote", {
              params: { path: { round_id: roundId } },
            }),
          ),
    onMutate: async ({ challengeId }) => {
      await queryClient.cancelQueries({ queryKey: currentRoundKey });
      const previous = queryClient.getQueryData<Round>(currentRoundKey);
      if (previous)
        queryClient.setQueryData<Round>(currentRoundKey, { ...previous, my_vote: challengeId });
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(currentRoundKey, context.previous);
    },
    onSuccess: (round) => queryClient.setQueryData(currentRoundKey, round),
    onSettled: invalidate,
  });
}

export function useChoose() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ roundId, challengeId }: { roundId: string; challengeId: string }) =>
      call(
        api.PUT("/api/v1/rounds/{round_id}/choice", {
          params: { path: { round_id: roundId } },
          body: { challenge_id: challengeId },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useParticipation(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (takePart: boolean) => {
      const options = { params: { path: { challenge_id: id } } };
      return takePart
        ? call(api.PUT("/api/v1/challenges/{challenge_id}/participation", options))
        : call(api.DELETE("/api/v1/challenges/{challenge_id}/participation", options));
    },
    onSuccess: (detail) => {
      queryClient.setQueryData(challengeKey(id), detail);
      void queryClient.invalidateQueries({ queryKey: challengesKey });
    },
  });
}
