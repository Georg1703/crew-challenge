import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { monthAndYear, todayIn } from "@/shared/lib/format";
import { Avatar, Banner, Button, DayGrid, DayMark, Icon, Skeleton } from "@/shared/ui";

import { useBoard } from "../api";
import styles from "../checkins.module.css";

const LEGEND = ["done", "missed", "todo", "not_due"] as const;

/** "2026-11" from a date ("2026-11-10"), and months moved by `offset`. */
function monthKey(day: string, offset = 0): string {
  const [year = 0, month = 1] = day.split("-").map(Number);
  const index = year * 12 + month - 1 + offset;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
}

/** A scheduled challenge's month: everyone's days as squares, with the streak per person. */
export function ChallengeBoard({
  challengeId,
  startDate,
  endDate,
  timeZone,
}: {
  challengeId: string;
  startDate: string;
  endDate: string;
  timeZone: string;
}) {
  const { t, i18n } = useTranslation();
  const today = todayIn(timeZone);
  const first = monthKey(startDate);
  const last = monthKey(endDate);
  const initial = monthKey(today) < first ? first : monthKey(today) > last ? last : monthKey(today);
  const [month, setMonth] = useState(initial);
  const board = useBoard(challengeId, month);
  const title = monthAndYear(`${month}-01`, i18n.language);

  return (
    <section className={styles.section}>
      <div className={styles.boardHead}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        {first !== last && (
          <span className={styles.boardNav}>
            <Button
              variant="ghost"
              aria-label={t("checkins.board.previous")}
              disabled={month <= first}
              icon={<Icon name="chevronLeft" size={20} />}
              onClick={() => setMonth(monthKey(`${month}-01`, -1))}
            />
            <Button
              variant="ghost"
              aria-label={t("checkins.board.next")}
              disabled={month >= last}
              icon={<Icon name="chevronRight" size={20} />}
              onClick={() => setMonth(monthKey(`${month}-01`, 1))}
            />
          </span>
        )}
      </div>
      {board.isPending && <Skeleton lines={3} />}
      {board.error && <Banner tone="danger" title={errorMessage(t, board.error)} />}
      {board.data && (
        <>
          <DayGrid
            label={t("checkins.board.label", { month: title })}
            days={board.data.days.map((day) => Number(day.slice(8, 10)))}
            todayIndex={board.data.days.indexOf(today)}
            dayName={(name, day, state) =>
              t("checkins.board.cell", { name, day, state: t(`checkins.states.${state}`) })
            }
            rows={board.data.rows.map((row) => ({
              key: row.member.id,
              name:
                row.streak !== null && row.streak > 0
                  ? t("checkins.board.nameStreak", {
                      name: row.member.display_name,
                      n: row.streak,
                    })
                  : row.member.display_name,
              leading: (
                <Avatar name={row.member.display_name} seed={row.member.avatar_seed} size="sm" />
              ),
              states: row.states,
            }))}
          />
          <ul className={styles.legend}>
            {LEGEND.map((state) => (
              <li key={state} className={styles.legendItem}>
                <DayMark state={state} size="md" label={t(`checkins.states.${state}`)} />
                <span className={styles.meta} aria-hidden="true">
                  {t(`checkins.states.${state}`)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
