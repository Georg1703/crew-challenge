import { useShallow } from "zustand/react/shallow";

import type { Proof } from "./api";
import { useUploads } from "./uploads/store";

/**
 * Where a subject's draft files stand, for the button that posts them: whether one still uploads
 * (on this phone, or a paused one the server knows of), and how many are uploaded and ready. A
 * file being removed (its "Undo" still runs) counts as gone, so the button never posts it.
 */
export function useDrafts(subject: string, proofs: Proof[]): { uploading: boolean; ready: number } {
  const removing = useUploads((s) => s.removing);
  const sending = useUploads(
    useShallow((s) =>
      Object.values(s.items).filter((u) => u.subject === subject && u.state !== "failed"),
    ),
  );
  const drafts = proofs.filter((p) => !p.posted && p.status !== "failed" && !removing[p.id]);
  return {
    uploading:
      sending.some((u) => !removing[u.proofId]) || drafts.some((p) => p.status === "uploading"),
    ready: drafts.filter((p) => p.status === "processing" || p.status === "ready").length,
  };
}
