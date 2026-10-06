import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useShallow } from "zustand/react/shallow";

import { errorMessage } from "@/i18n/errors";
import {
  Button,
  ProofAddTile,
  ProofTile,
  ProofViewer,
  Sheet,
  useToast,
  type ProofTileState,
} from "@/shared/ui";

import { checkinsKey, proofApi, type Proof, type TodayChallenge } from "../api";
import styles from "../checkins.module.css";
import { cancel, retry, toggle, upload } from "../uploads/engine";
import { useUploads } from "../uploads/store";

const MAX_PROOFS = 5; // the API refuses a 6th too
const UNDO_MS = 5000; // as long as the toast with "Undo" stays
const GiB = 1024 ** 3;
const ASK_ABOVE = 2 * GiB; // on a phone, a bigger video asks first

const ACCEPT: Record<string, string> = {
  photo: "image/*",
  video: "video/*",
  photo_or_video: "image/*,video/*",
};

/** A saved proof's tile: an upload that never finished shows as waiting for the file again. */
const SAVED_STATE: Record<Proof["status"], ProofTileState> = {
  uploading: "paused",
  processing: "processing",
  ready: "ready",
  failed: "failed",
};

const onPhone = () => window.matchMedia?.("(pointer: coarse)").matches ?? false;

/**
 * Today's proofs for one challenge, under its check-in: what the crew sees, this phone's uploads
 * in flight, and "+" while fewer than 5. Uploads keep going on other screens (uploads/engine.ts).
 */
export function ProofRow({ card, day }: { card: TodayChallenge; day: string }) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const local = useUploads(
    useShallow((s) => Object.values(s.items).filter((u) => u.challengeId === card.id)),
  );
  const [hidden, setHidden] = useState<string[]>([]); // removed, until "Undo" runs out
  const [viewing, setViewing] = useState<number | null>(null);
  const [big, setBig] = useState<File | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: checkinsKey });
  const inFlight = new Set(local.map((u) => u.proofId));
  const saved = card.proofs.filter((p) => !inFlight.has(p.id) && !hidden.includes(p.id));
  const sending = local.filter((u) => !hidden.includes(u.proofId));
  const viewable = saved.filter((p) => p.url);
  const counted = sending.length + saved.filter((p) => p.status !== "failed").length;
  const kind = (k: string) => t(`proofs.kind.${k}`);

  const send = (file: File) =>
    void upload({ challengeId: card.id, day, file, onDone: refresh }).catch((error: unknown) =>
      toast(errorMessage(t, error), "error"),
    );

  const remove = (proofId: string, uploadId?: string) => {
    setHidden((h) => [...h, proofId]);
    let undone = false;
    toast(t("proofs.removed"), "info", {
      label: t("checkins.undo"),
      onClick: () => {
        undone = true;
        setHidden((h) => h.filter((id) => id !== proofId));
      },
    });
    window.setTimeout(() => {
      if (undone) return;
      void (async () => {
        try {
          if (uploadId) await cancel(uploadId);
          await proofApi.remove(proofId);
        } catch (error) {
          toast(errorMessage(t, error), "error");
        }
        await refresh();
      })();
    }, UNDO_MS);
  };

  return (
    <div className={styles.proofs}>
      {saved.map((proof) => {
        const at = viewable.indexOf(proof);
        const waiting = proof.status === "uploading";
        return (
          <ProofTile
            key={proof.id}
            kind={proof.kind}
            state={SAVED_STATE[proof.status]}
            src={proof.thumb_url ?? (proof.kind === "photo" ? proof.url : null)}
            label={t(
              `proofs.tile.${waiting ? "waiting" : proof.status === "failed" ? "failedSaved" : proof.status}`,
              { kind: kind(proof.kind) },
            )}
            onOpen={
              at >= 0
                ? () => setViewing(at)
                : waiting
                  ? () => toast(t("proofs.pickAgain"))
                  : undefined
            }
            onRemove={() => remove(proof.id)}
            removeLabel={t("proofs.remove")}
          />
        );
      })}
      {sending.map((u) => (
        <ProofTile
          key={u.id}
          kind={u.kind}
          state={u.state}
          progress={u.progress}
          src={u.preview}
          label={t(`proofs.tile.${u.state}`, {
            kind: kind(u.kind),
            percent: Math.round(u.progress * 100),
          })}
          onOpen={() => void (u.state === "failed" ? retry(u.id) : toggle(u.id))}
          onRemove={() => remove(u.proofId, u.id)}
          removeLabel={t("proofs.remove")}
        />
      ))}
      {counted < MAX_PROOFS && (
        <ProofAddTile
          accept={ACCEPT[card.proof_kind] ?? "image/*"}
          label={t("proofs.add")}
          onPick={(file) => (file.size > ASK_ABOVE && onPhone() ? setBig(file) : send(file))}
        />
      )}

      <ProofViewer
        items={viewable.map((p) => ({
          key: p.id,
          kind: p.kind,
          src: p.url ?? "",
          hlsSrc: p.hls_url,
          poster: p.thumb_url,
          caption: card.title,
        }))}
        index={viewing ?? 0}
        onIndexChange={setViewing}
        open={viewing !== null}
        onClose={() => setViewing(null)}
        label={t("proofs.viewer.label")}
        closeLabel={t("common.close")}
        previousLabel={t("proofs.viewer.previous")}
        nextLabel={t("proofs.viewer.next")}
      />
      <Sheet
        open={big !== null}
        onClose={() => setBig(null)}
        title={t("proofs.bigTitle", {
          size: new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1 }).format(
            (big?.size ?? 0) / GiB,
          ),
        })}
        closeLabel={t("common.close")}
      >
        <p className={styles.muted}>{t("proofs.bigBody")}</p>
        <Button
          size="lg"
          onClick={() => {
            if (big) send(big);
            setBig(null);
          }}
        >
          {t("proofs.bigUpload")}
        </Button>
      </Sheet>
    </div>
  );
}
