import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useShallow } from "zustand/react/shallow";

import { ChallengeIcon } from "@/features/challenges";
import { ProofTiles, useUploads } from "@/features/proofs";
import { errorMessage } from "@/i18n/errors";
import { cx } from "@/shared/lib/cx";
import { weekday } from "@/shared/lib/dates";
import { formatNumber } from "@/shared/lib/format";
import { tap } from "@/shared/lib/haptics";
import {
  Button,
  Card,
  HoldButton,
  Icon,
  ProgressBar,
  StatusPill,
  WeekStrip,
  useToast,
} from "@/shared/ui";

import {
  checkInProofs,
  checkinsKey,
  useCheckIn,
  useUndoCheckIn,
  type TodayChallenge,
} from "../api";
import styles from "../checkins.module.css";
import { shortWindow, windowKind } from "../windows";
import { AmountSheet } from "./AmountSheet";

const QUICK_AMOUNTS = [1, 5, 10] as const;

/**
 * One of my challenges today: photos or videos (uploaded first, as drafts), then check in (hold,
 * or add a number), the week, the streak. The posting buttons wait while files upload and, where
 * proof is asked, until one has finished.
 */
export function CheckInCard({
  card,
  day,
  linked = false,
}: {
  card: TodayChallenge;
  day: string;
  /** The head opens the challenge's page (on Today; not in the check-in sheet). */
  linked?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const checkIn = useCheckIn();
  const undo = useUndoCheckIn();
  const [typing, setTyping] = useState(false);
  const quantity = card.measure === "quantity";
  const notDue = card.state === "not_due";
  const subject = checkInProofs(card.id, day);
  const sending = useUploads(
    useShallow((s) =>
      Object.values(s.items).filter((u) => u.subject === subject.key && u.state !== "failed"),
    ),
  );
  const drafts = card.proofs.filter((p) => !p.posted && p.status !== "failed");
  const uploading = sending.length > 0 || drafts.some((p) => p.status === "uploading");
  const ready = drafts.filter((p) => p.status === "processing" || p.status === "ready").length;
  const opened = quantity ? (card.total ?? 0) > 0 : card.state === "done";
  // What keeps a check-in or a "+N" back: uploads still running, or proof asked and none ready.
  const waiting = uploading ? "uploading" : card.proof_required && ready === 0 ? "proof" : null;
  const canAddFiles = opened && ready > 0 && !uploading; // files alone, after the check-in

  const record = (amount: number | null) =>
    checkIn.mutate(
      { card, day, amount },
      {
        onSuccess: () => {
          tap();
          toast(
            amount !== null
              ? t("checkins.added", {
                  amount: formatNumber(amount, i18n.language),
                  unit: card.unit,
                })
              : opened
                ? t("checkins.filesPosted")
                : t("checkins.checkedIn"),
            "success",
            {
              label: t("checkins.undo"),
              onClick: () =>
                undo.mutate(
                  { id: card.id, day },
                  {
                    onSuccess: () => toast(t("checkins.undone")),
                    onError: (error) => toast(errorMessage(t, error), "error"),
                  },
                ),
            },
          );
        },
        onError: (error) => toast(errorMessage(t, error), "error"),
      },
    );

  const target = card.day_min;
  const head = (
    <>
      <ChallengeIcon icon={card.icon} tone={card.state === "done" ? "neutral" : "accent"} />
      <h2 className={styles.cardTitle}>{card.title}</h2>
      {card.streak !== null && card.streak > 0 && (
        <StatusPill tone="success">{t("checkins.streak", { n: card.streak })}</StatusPill>
      )}
    </>
  );
  const total = card.total ?? 0;
  const current = card.current;
  const short = current && shortWindow(t, current, card, i18n.language);

  return (
    <Card className={styles.card}>
      {linked ? (
        <Link to={`/challenges/${card.id}`} className={cx(styles.cardHead, styles.cardLink)}>
          {head}
          <Icon name="chevronRight" size={20} />
        </Link>
      ) : (
        <div className={styles.cardHead}>{head}</div>
      )}

      {quantity ? (
        <div className={styles.amounts}>
          <div className={styles.total}>
            <span className={styles.totalNumber}>
              {target
                ? t("checkins.totalOf", {
                    total: formatNumber(total, i18n.language),
                    goal: formatNumber(target, i18n.language),
                    unit: card.unit,
                  })
                : t("checkins.totalToday", {
                    total: formatNumber(total, i18n.language),
                    unit: card.unit,
                  })}
            </span>
            {card.state === "done" && (
              <StatusPill tone="success">{t("checkins.doneShort")}</StatusPill>
            )}
          </div>
          {target ? (
            <ProgressBar
              value={total}
              max={target}
              label={t("checkins.totalOf", {
                total: formatNumber(total, i18n.language),
                goal: formatNumber(target, i18n.language),
                unit: card.unit,
              })}
            />
          ) : null}
          <div className={styles.chips}>
            {QUICK_AMOUNTS.map((amount) => (
              <Button
                key={amount}
                variant="secondary"
                disabled={notDue || waiting !== null}
                onClick={() => record(amount)}
              >
                {t("checkins.plus", { n: amount })}
              </Button>
            ))}
            <Button
              variant="secondary"
              disabled={notDue || waiting !== null}
              onClick={() => setTyping(true)}
            >
              {t("checkins.other")}
            </Button>
          </div>
        </div>
      ) : (
        <HoldButton
          label={
            notDue
              ? t("checkins.notDue")
              : card.measure === "abstain"
                ? t("checkins.holdAbstain")
                : t("checkins.hold")
          }
          doneLabel={
            card.measure === "abstain" ? t("checkins.doneAbstain") : t("checkins.doneToday")
          }
          done={card.state === "done"}
          disabled={notDue || waiting !== null}
          onConfirm={() => record(null)}
        />
      )}

      {!notDue && waiting !== null && !(opened && !quantity) && (
        <p className={styles.meta}>{t(`checkins.waiting.${waiting}`)}</p>
      )}

      {current && (
        <div className={styles.window}>
          <p className={styles.meta}>
            {t(`windows.progress.${card.need_kind}.${windowKind(card)}`, {
              done: formatNumber(current.done ?? 0, i18n.language),
              goal: formatNumber(current.need, i18n.language),
              unit: card.unit,
            })}
          </p>
          {short && <StatusPill tone="warning">{short}</StatusPill>}
        </div>
      )}

      <WeekStrip
        label={t("checkins.weekLabel")}
        days={card.week.map((d) => ({
          key: d.day,
          letter: t(`challenges.days.short.${weekday(d.day)}`),
          name: `${t(`challenges.days.long.${weekday(d.day)}`)}: ${t(`checkins.states.${d.state}`)}${card.proof_days.includes(d.day) ? t("checkins.withProof") : ""}`,
          state: d.state,
          today: d.day === day,
          proof: card.proof_days.includes(d.day),
        }))}
      />

      {!notDue && (
        <ProofTiles
          subject={subject}
          title={card.title}
          proofs={card.proofs}
          onChanged={() => queryClient.invalidateQueries({ queryKey: checkinsKey })}
          onUploaded={() => toast(t("checkins.readyToPost", { title: card.title }))}
        />
      )}
      {canAddFiles && (
        <Button variant="secondary" onClick={() => record(null)}>
          {t("checkins.postFiles", { count: ready })}
        </Button>
      )}

      {typing && <AmountSheet unit={card.unit} onClose={() => setTyping(false)} onAdd={record} />}
    </Card>
  );
}
