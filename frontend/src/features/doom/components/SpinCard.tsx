import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { CHALLENGE_ICONS } from "@/features/challenges";
import { ProofTiles } from "@/features/proofs";
import { errorMessage } from "@/i18n/errors";
import { formatDayLong } from "@/shared/lib/format";
import { Button, Card, ChallengeChip, Dial, StatusPill, useToast } from "@/shared/ui";

import { spinProofs, spinsKey, useDone, useDraw, type Spin } from "../api";
import { describeFailed } from "../describe";
import styles from "../doom.module.css";

/**
 * One spin on /spins: what failed, then the dial. "Spin" asks the server, which draws the
 * punishment; the dial turns to it and, once it stops, the card asks for proof or for "Done".
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
            {drawn.proof_required ? (
              <ProofTiles
                drafts={false}
                subject={spinProofs(spin.id)}
                title={drawn.text}
                proofs={spin.proofs}
                onChanged={() => queryClient.invalidateQueries({ queryKey: spinsKey })}
              />
            ) : (
              <Button
                variant="secondary"
                size="lg"
                loading={done.isPending}
                onClick={() =>
                  done.mutate(spin.id, {
                    onSuccess: () => toast(t("doom.served"), "success"),
                    onError: (error) => toast(errorMessage(t, error), "error"),
                  })
                }
              >
                {t("doom.done")}
              </Button>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
