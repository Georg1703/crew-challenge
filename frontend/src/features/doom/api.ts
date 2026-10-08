import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call, type components } from "@/api";
import type { ProofSubject } from "@/features/proofs";

export type Owed = components["schemas"]["OwedOut"];
export type Spin = components["schemas"]["SpinOut"];
export type SpinItem = components["schemas"]["SpinItemOut"];

export const spinsKey = ["spins"] as const;

/** My spins not served yet, with how many to spin and to serve (the Today card, /spins). */
export function useSpins() {
  return useQuery({ queryKey: spinsKey, queryFn: () => call(api.GET("/api/v1/spins")) });
}

/** Put a changed spin into the cached list (served ones leave it on the next refresh). */
function useReplace() {
  const client = useQueryClient();
  return (spin: Spin) =>
    client.setQueryData<Owed>(spinsKey, (owed) =>
      owed ? { ...owed, spins: owed.spins.map((s) => (s.id === spin.id ? spin : s)) } : owed,
    );
}

/** Spin: the server draws the punishment; the dial then turns to it. */
export function useDraw() {
  const replace = useReplace();
  return useMutation({
    mutationFn: (id: string) =>
      call(api.POST("/api/v1/spins/{spin_id}/draw", { params: { path: { spin_id: id } } })),
    onSuccess: replace,
  });
}

/** Serve a punishment that needs no proof. */
export function useDone() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      call(api.POST("/api/v1/spins/{spin_id}/done", { params: { path: { spin_id: id } } })),
    onSettled: () => client.invalidateQueries({ queryKey: spinsKey }),
  });
}

/** A drawn spin as a proof subject for the upload engine. */
export function spinProofs(spinId: string): ProofSubject {
  return {
    key: `spin:${spinId}`,
    start: (body) =>
      call(
        api.POST("/api/v1/spins/{spin_id}/proofs", {
          params: { path: { spin_id: spinId } },
          body,
        }),
      ),
    resume: (fingerprint) =>
      call(
        api.GET("/api/v1/spins/{spin_id}/proofs/resume", {
          params: { path: { spin_id: spinId }, query: { fingerprint } },
        }),
      ),
  };
}
