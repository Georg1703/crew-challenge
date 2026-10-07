import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ChallengeIcon } from "@/features/challenges";
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

import { useCheckIn, useUndoCheckIn, type TodayChallenge } from "../api";
import styles from "../checkins.module.css";
import { AmountSheet } from "./AmountSheet";
import { ProofRow } from "./ProofRow";

const QUICK_AMOUNTS = [1, 5, 10] as const;

/** One of my challenges today: check in (hold, or add a number), the week, the streak. */
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
  const checkIn = useCheckIn();
  const undo = useUndoCheckIn();
  const [typing, setTyping] = useState(false);
  const quantity = card.measure === "quantity";
  const notDue = card.state === "not_due";

  const record = (amount: number | null) =>
    checkIn.mutate(
      { card, day, amount },
      {
        onSuccess: () => {
          tap();
          toast(
            amount === null
              ? t("checkins.checkedIn")
              : t("checkins.added", {
                  amount: formatNumber(amount, i18n.language),
                  unit: card.unit,
                }),
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
                disabled={notDue}
                onClick={() => record(amount)}
              >
                {t("checkins.plus", { n: amount })}
              </Button>
            ))}
            <Button variant="secondary" disabled={notDue} onClick={() => setTyping(true)}>
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
          disabled={notDue}
          onConfirm={() => record(null)}
        />
      )}

      {card.progress && (
        <p className={styles.meta}>
          {t(
            `checkins.progress.${card.progress.kind}.${card.window === "week" || card.window === "month" ? card.window : "period"}`,
            {
              done: formatNumber(card.progress.done, i18n.language),
              goal: formatNumber(card.progress.goal, i18n.language),
              unit: card.unit,
            },
          )}
        </p>
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

      {card.proof_kind !== "none" && (card.state === "done" || card.state === "partial") && (
        <>
          {card.proof_required && card.proofs.length === 0 && (
            <p className={styles.meta}>{t("proofs.nudge")}</p>
          )}
          <ProofRow card={card} day={day} />
        </>
      )}

      {typing && <AmountSheet unit={card.unit} onClose={() => setTyping(false)} onAdd={record} />}
    </Card>
  );
}
