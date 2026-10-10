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

import { proofApi, type Proof, type ProofSubject } from "../api";
import { viewerItem } from "../proofs";
import styles from "../proofs.module.css";
import { cancel, retry, toggle, upload } from "../uploads/engine";
import { useUploads } from "../uploads/store";

const MAX_PROOFS = 5; // a post's; the API refuses a 6th too
const UNDO_MS = 5000; // as long as the toast with "Undo" stays
const GiB = 1024 ** 3;
const ASK_ABOVE = 2 * GiB; // on a phone, a bigger video asks first

/** What "+" offers: a photo or a video, asked first (see ProofAddTile). */
const PICKERS = [
  { accept: "image/*", icon: "image", label: "proofs.addPhoto" },
  { accept: "video/*", icon: "video", label: "proofs.addVideo" },
] as const;

/** A saved proof's tile: an upload that never finished shows as waiting for the file again. */
const SAVED_STATE: Record<Proof["status"], ProofTileState> = {
  uploading: "paused",
  processing: "processing",
  ready: "ready",
  failed: "failed",
};

const onPhone = () => window.matchMedia?.("(pointer: coarse)").matches ?? false;

/**
 * A subject's proofs (today's check-in, a spin): what the API has, this phone's uploads in flight,
 * and "+" while the post to come has fewer than 5. New files are draft files of that post,
 * removable until it is made; posted ones stay. Uploads keep going on other screens
 * (uploads/engine.ts). `title` names them in the viewer; `onChanged` refreshes whatever shows
 * `proofs`; `onUploaded` runs when the last upload in flight here has finished.
 */
export function ProofTiles({
  subject,
  title,
  proofs,
  onChanged,
  onUploaded,
}: {
  subject: ProofSubject;
  title: string;
  proofs: Proof[];
  onChanged: () => Promise<unknown>;
  onUploaded?: () => void;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const local = useUploads(
    useShallow((s) => Object.values(s.items).filter((u) => u.subject === subject.key)),
  );
  const [hidden, setHidden] = useState<string[]>([]); // removed, until "Undo" runs out
  const [viewing, setViewing] = useState<number | null>(null);
  const [big, setBig] = useState<File | null>(null);

  const inFlight = new Set(local.map((u) => u.proofId));
  const saved = proofs.filter((p) => !inFlight.has(p.id) && !hidden.includes(p.id));
  const sending = local.filter((u) => !hidden.includes(u.proofId));
  const viewable = saved.filter((p) => p.url);
  const counted = sending.length + saved.filter((p) => p.status !== "failed" && !p.posted).length;
  const kind = (k: string) => t(`proofs.kind.${k}`);

  const finished = async (proofId: string) => {
    await onChanged();
    const others = Object.values(useUploads.getState().items).some(
      (u) => u.subject === subject.key && u.proofId !== proofId && u.state !== "failed",
    );
    if (!others) onUploaded?.();
  };
  const send = (file: File) =>
    void upload({ subject, file, onDone: finished }).catch((error: unknown) =>
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
        await onChanged();
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
            fallbackSrc={proof.phone_thumb_url}
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
            onRemove={proof.posted ? undefined : () => remove(proof.id)}
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
          choices={PICKERS.map((picker) => ({ ...picker, label: t(picker.label) }))}
          label={t("proofs.add")}
          closeLabel={t("common.close")}
          onPick={(file) => (file.size > ASK_ABOVE && onPhone() ? setBig(file) : send(file))}
        />
      )}

      <ProofViewer
        items={viewable.map((p) => viewerItem(p, title))}
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
