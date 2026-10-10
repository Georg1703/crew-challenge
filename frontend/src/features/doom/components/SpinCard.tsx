import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useShallow } from "zustand/react/shallow";

import { CHALLENGE_ICONS } from "@/features/challenges";
import { ProofTiles, useUploads } from "@/features/proofs";
import { errorMessage } from "@/i18n/errors";
import { formatDayLong } from "@/shared/lib/format";
import { Button, Card, ChallengeChip, Dial, StatusPill, useToast } from "@/shared/ui";

import { spinProofs, spinsKey, useDone, useDraw, type Spin } from "../api";
import { describeFailed } from "../describe";
import styles from "../doom.module.css";

/**
 * One spin on /spins: what failed, then the dial. "Spin" asks the server, which draws the
 * punishment; the dial turns to it and, once it stops, the card asks for "Done" or, when it needs
 * proof, for photos or videos (uploaded first, as drafts) and "Serve", which waits for them.
 */
export function SpinCard({ spin }: { spin: Spin }) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const draw = useDraw();
  const done = useDone();
  const [stopped, setStopped] = useState(spin.state !== "pending");
  const drawn = spin.punishment;
  const count = spin.punishments.length;
  const language = i18n.language;
  const subject = spinProofs(spin.id);
  const sending = useUploads(
    useShallow((s) =>
      Object.values(s.items).filter((u) => u.subject === subject.key && u.state !== "failed"),
    ),
  );
  const drafts = spin.proofs.filter((p) => !p.posted && p.status !== "failed");
  const uploading = sending.length > 0 || drafts.some((p) => p.status === "uploading");
  const ready = drafts.filter((p) => p.status === "processing" || p.status === "ready").length;
  const serve = () =>
    done.mutate(spin.id, {
      onSuccess: () => toast(t("doom.served"), "success"),
      onError: (error) => toast(errorMessage(t, error), "error"),
    });

  const center = !drawn ? (
    <span className={styles.unknown} aria-hidden="true">
      {"?"}
    </span>
  ) : stopped ? (
    <span className={styles.number} aria-hidden="true">
      {drawn.position}
    </span>
  ) : null;

  return (
    <Card>
      <div className={styles.stack}>
        <div className={styles.result}>
          <ChallengeChip icon={CHALLENGE_ICONS[spin.challenge.icon]} label={spin.challenge.title} />
          <span className={styles.meta}>{describeFailed(t, spin, language)}</span>
        </div>

        <Dial
          count={count}
          drawn={drawn?.position ?? null}
          label={
            drawn && stopped
              ? t("doom.dialDrawn", { count, position: drawn.position, text: drawn.text })
              : t("doom.dial", { count })
          }
          onStopped={() => setStopped(true)}
        >
          {center}
        </Dial>

        {!stopped || !drawn ? (
          <>
            <ol className={styles.list} aria-label={t("challenges.punishments.title")}>
              {spin.punishments.map((p) => (
                <li key={p.position} className={styles.row}>
                  <span className={styles.badge}>{p.position}</span>
                  <span className={styles.text}>{p.text}</span>
                  <span className={styles.meta}>
                    {p.proof_required ? t("doom.withProof") : t("doom.noProof")}
                  </span>
                </li>
              ))}
            </ol>
            <Button
              size="lg"
              loading={draw.isPending || (drawn !== null && !stopped)}
              onClick={() =>
                draw.mutate(spin.id, { onError: (error) => toast(errorMessage(t, error), "error") })
              }
            >
              {t("doom.spin")}
            </Button>
            <p className={styles.meta}>{t("doom.odds", { count })}</p>
          </>
        ) : (
          <>
            <div className={styles.result} role="status">
              <h2 className={styles.title}>{drawn.text}</h2>
              {spin.late && spin.serve_by ? (
                <span>
                  <StatusPill tone="danger">{t("doom.late")}</StatusPill>{" "}
                  <span className={styles.meta}>
                    {t("doom.wasDue", { date: formatDayLong(spin.serve_by, language) })}
                  </span>
                </span>
              ) : (
                spin.serve_by && (
                  <span className={styles.meta}>
                    {t("doom.serveBy", { date: formatDayLong(spin.serve_by, language) })}
                  </span>
                )
              )}
            </div>
            {spin.state === "served" ? null : drawn.proof_required ? (
              <>
                <ProofTiles
                  subject={subject}
                  title={drawn.text}
                  proofs={spin.proofs}
                  onChanged={() => queryClient.invalidateQueries({ queryKey: spinsKey })}
                  onUploaded={() => toast(t("doom.readyToServe"))}
                />
                {(uploading || ready === 0) && (
                  <p className={styles.meta}>
                    {t(uploading ? "doom.waitingUploads" : "doom.addProof")}
                  </p>
                )}
                <Button
                  size="lg"
                  disabled={uploading || ready === 0}
                  loading={done.isPending}
                  onClick={serve}
                >
                  {t("doom.serve")}
                </Button>
              </>
            ) : (
              <Button variant="secondary" size="lg" loading={done.isPending} onClick={serve}>
                {t("doom.done")}
              </Button>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
