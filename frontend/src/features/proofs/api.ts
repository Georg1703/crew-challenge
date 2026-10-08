import { useQuery } from "@tanstack/react-query";

import { api, call, type components } from "@/api";

export type Proof = components["schemas"]["ProofOut"];
export type ProofUpload = components["schemas"]["ProofUploadOut"];
export type ProofStart = components["schemas"]["ProofStartInRequest"];

/**
 * What a proof backs, as the upload engine sees it: starting a proof on it, and resuming this
 * phone's unfinished upload of a file on it (rejected with 404 when there is none). `key` groups
 * this phone's uploads for the tiles.
 */
export interface ProofSubject {
  key: string;
  start: (body: ProofStart) => Promise<ProofUpload>;
  resume: (fingerprint: string) => Promise<ProofUpload>;
}

/**
 * Proof calls for the upload engine (which runs outside React, see uploads/engine.ts), whatever the
 * proof backs. Starting and resuming one belong to its subject (a `ProofSubject`).
 */
export const proofApi = {
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
