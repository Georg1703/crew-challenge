import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ChallengeIcon } from "@/features/challenges";
import { errorMessage } from "@/i18n/errors";
import { tap } from "@/shared/lib/haptics";
import {
  Button,
  Card,
  HoldButton,
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

/** Number with at most two decimals, in the UI language. */
function format(value: number, language: string): string {
  return new Intl.NumberFormat(language, { maximumFractionDigits: 2 }).format(value);
}

/** Weekday index, Monday = 0, of a crew-local date ("2026-11-10"). */
function weekday(day: string): number {
  return (new Date(`${day}T00:00:00Z`).getUTCDay() + 6) % 7;
}

/** One of my challenges today: check in (hold, or add a number), the week, the streak. */
export function CheckInCard({ card, day }: { card: TodayChallenge; day: string }) {
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
              : t("checkins.added", { amount: format(amount, i18n.language), unit: card.unit }),
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

  const target = card.target_scope === "per_check_in" ? card.target_value : null;
  const total = card.total ?? 0;

  return (
    <Card className={styles.card}>
      <div className={styles.cardHead}>
        <ChallengeIcon icon={card.icon} tone={card.state === "done" ? "neutral" : "accent"} />
        <h2 className={styles.cardTitle}>{card.title}</h2>
        {card.streak !== null && card.streak > 0 && (
          <StatusPill tone="success">{t("checkins.streak", { n: card.streak })}</StatusPill>
        )}
      </div>

      {quantity ? (
        <div className={styles.amounts}>
          <div className={styles.total}>
            <span className={styles.totalNumber}>
              {target
                ? t("checkins.totalOf", {
                    total: format(total, i18n.language),
                    goal: format(target, i18n.language),
                    unit: card.unit,
                  })
                : t("checkins.totalToday", {
                    total: format(total, i18n.language),
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
                total: format(total, i18n.language),
                goal: format(target, i18n.language),
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
            `checkins.progress.${card.progress.kind}.${card.frequency === "times_per_week" || card.target_scope === "per_week" ? "week" : "period"}`,
            {
              done: format(card.progress.done, i18n.language),
              goal: format(card.progress.goal, i18n.language),
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
          name: `${t(`challenges.days.long.${weekday(d.day)}`)}: ${t(`checkins.states.${d.state}`)}`,
          state: d.state,
          today: d.day === day,
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
