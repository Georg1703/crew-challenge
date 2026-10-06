import type { TFunction } from "i18next";

import { formatDuration } from "@/shared/lib/format";
import type { FeedProof, ViewerItem } from "@/shared/ui";

import type { Proof } from "./api";

/** A ProofMosaic shows three proofs, the third with "+N". */
export const SHOWN_PROOFS = 3;

/** A proof the crew can see (processing or ready) as a tile; `who` names it for screen readers. */
export function shownTile(proof: Proof, t: TFunction, who: string): FeedProof {
  const processing = proof.status === "processing";
  return {
    key: proof.id,
    kind: proof.kind,
    state: processing ? "processing" : "ready",
    src: proof.thumb_url ?? (proof.kind === "photo" ? proof.url : null),
    full: proof.kind === "photo" ? proof.url : null, // a video keeps its poster
    duration: proof.duration === null ? undefined : formatDuration(proof.duration),
    label: t(processing ? "feed.proofProcessing" : "feed.proof", {
      kind: t(`proofs.kind.${proof.kind}`),
      name: who,
    }),
  };
}

/** A proof full screen: the original, or HLS once a video is transcoded (production). */
export function viewerItem(proof: Proof, caption: string): ViewerItem {
  return {
    key: proof.id,
    kind: proof.kind,
    src: proof.url ?? "",
    hlsSrc: proof.hls_url,
    poster: proof.thumb_url,
    caption,
  };
}
