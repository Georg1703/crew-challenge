import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { cx } from "@/shared/lib/cx";
import { formatDay, formatDayLong, monthAndYear, todayIn } from "@/shared/lib/format";
import {
  Avatar,
  Banner,
  Button,
  DayBar,
  DayBars,
  DayBarsAxis,
  Icon,
  ProgressBar,
  Skeleton,
  StatusPill,
  type DayState,
} from "@/shared/ui";

import { useBoard, type Board } from "../api";
import styles from "../checkins.module.css";
import { DaySheet } from "./DaySheet";

const LEGEND = ["done", "missed", "todo", "future"] as const;
const LEFT_TODAY: DayState[] = ["todo", "partial"];
const DAY_MS = 86_400_000;

/** "2026-11" from a date ("2026-11-10"), and months moved by `offset`. */
function monthKey(day: string, offset = 0): string {
  const [year = 0, month = 1] = day.split("-").map(Number);
  const index = year * 12 + month - 1 + offset;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
}

/** Whole days from `a` to `b` (dates as "YYYY-MM-DD"). */
function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(b) - Date.parse(a)) / DAY_MS);
}

function count(states: DayState[], state: DayState): number {
  return states.filter((s) => s === state).length;
}

/**
 * A scheduled challenge's month: where the month is, the crew's totals, and a row of day bars per
 * person (most days done first), with their streak and whether today is still open. A dot marks a
 * day with proof; tapping a day (its number, or the bars) opens that day for everyone.
 */
export function ChallengeBoard({
  challengeId,
  title = "",
  unit = "",
  startDate,
  endDate,
  timeZone,
  meId,
  fixedDays,
  leftOn = {},
}: {
  challengeId: string;
  title?: string;
  unit?: string;
  startDate: string;
  endDate: string;
  timeZone: string;
  meId?: string;
  /** Due on set days (daily, weekdays): scores read "done/due"; otherwise "N done". */
  fixedDays: boolean;
  /** When someone left early, by member id. */
  leftOn?: Record<string, string>;
}) {
  const { t, i18n } = useTranslation();
  const today = todayIn(timeZone);
  const first = monthKey(startDate);
  const last = monthKey(endDate);
  const initial = monthKey(today) < first ? first : monthKey(today) > last ? last : monthKey(today);
  const [month, setMonth] = useState(initial);
  const [sheetDay, setSheetDay] = useState<string | null>(null); // kept while the sheet closes
  const [dayOpen, setDayOpen] = useState(false);
  const openDay = (picked: string | undefined) => {
    if (!picked) return;
    setSheetDay(picked);
    setDayOpen(true);
  };
  const board = useBoard(challengeId, month);
  const monthTitle = monthAndYear(`${month}-01`, i18n.language);

  const total = daysBetween(startDate, endDate) + 1;
  const finished = today > endDate;
  const day = Math.min(total, daysBetween(startDate, today) + 1);

  return (
    <>
      <section className={styles.section} aria-label={t("checkins.board.whereLabel")}>
        <div className={styles.boardHead}>
          <span className={styles.strong}>
            {finished
              ? t("checkins.board.ended", { date: formatDay(endDate, i18n.language) })
              : t("checkins.board.dayOf", { day, total })}
          </span>
          {!finished && (
            <span className={styles.meta}>
              {t("checkins.board.daysLeft", { n: total - day + 1 })}
            </span>
          )}
        </div>
        <ProgressBar
          value={finished ? total : day}
          max={total}
          label={t("checkins.board.dayOf", { day, total })}
        />
        {board.data && <Totals board={board.data} today={today} finished={finished} />}
      </section>

      <section className={styles.section}>
        <div className={styles.boardHead}>
          <h2 className={styles.sectionTitle}>{t("checkins.board.title")}</h2>
          {first !== last && (
            <span className={styles.boardNav}>
              <span className={styles.meta}>{monthTitle}</span>
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
        {board.isPending && <Skeleton lines={4} />}
        {board.error && <Banner tone="danger" title={errorMessage(t, board.error)} />}
        {board.data && (
          <Rows
            board={board.data}
            today={today}
            meId={meId}
            fixedDays={fixedDays}
            leftOn={leftOn}
            onPick={(index) => openDay(board.data.days[index])}
          />
        )}
        <ul className={styles.legend}>
          {LEGEND.map((state) => (
            <li key={state} className={styles.legendItem}>
              <DayBar state={state} />
              <span className={styles.meta}>{t(`checkins.board.legend.${state}`)}</span>
            </li>
          ))}
          <li className={styles.legendItem}>
            <DayBar state="done" proof />
            <span className={styles.meta}>{t("checkins.board.legend.proof")}</span>
          </li>
        </ul>
      </section>
      {sheetDay && board.data && (
        <DaySheet
          challengeId={challengeId}
          title={title}
          unit={unit}
          days={board.data.days.filter((d) => d <= today)}
          day={sheetDay}
          open={dayOpen}
          onDay={setSheetDay}
          onClose={() => setDayOpen(false)}
        />
      )}
    </>
  );
}

/** The crew's days done and missed so far, and how many still have today to do. */
function Totals({ board, today, finished }: { board: Board; today: string; finished: boolean }) {
  const { t } = useTranslation();
  const index = board.days.indexOf(today);
  const all = board.rows.flatMap((row) => row.states);
  const left = board.rows.filter((row) => LEFT_TODAY.includes(row.states[index] ?? "outside"));
  const stats = [
    { key: "done", n: count(all, "done"), tone: styles.statDone },
    { key: "missed", n: count(all, "missed"), tone: styles.statMissed },
    ...(finished ? [] : [{ key: "today", n: left.length, tone: styles.statToday }]),
  ];
  return (
    <dl className={styles.stats}>
      {stats.map((stat) => (
        <div key={stat.key} className={styles.stat}>
          <dt className={styles.meta}>{t(`checkins.board.stats.${stat.key}`)}</dt>
          <dd className={cx(styles.statNumber, stat.tone)}>{stat.n}</dd>
        </div>
      ))}
    </dl>
  );
}

function Rows({
  board,
  today,
  meId,
  fixedDays,
  leftOn,
  onPick,
}: {
  board: Board;
  today: string;
  meId?: string;
  fixedDays: boolean;
  leftOn: Record<string, string>;
  onPick: (index: number) => void;
}) {
  const { t, i18n } = useTranslation();
  const index = board.days.indexOf(today);
  const rows = board.rows
    .map((row, order) => ({
      row,
      order,
      done: count(row.states, "done"),
      missed: count(row.states, "missed"),
    }))
    .sort((a, b) => b.done - a.done || a.order - b.order);

  return (
    <div className={styles.board}>
      <div className={styles.boardRow}>
        <DayBarsAxis
          days={board.days.map((d) => Number(d.slice(8, 10)))}
          todayIndex={index >= 0 ? index : undefined}
          onPick={(i) => (board.days[i] ?? "") <= today && onPick(i)}
          labels={board.days.map((d) => formatDayLong(d, i18n.language))}
        />
      </div>
      {rows.map(({ row, done, missed }) => {
        const name = row.member.display_name;
        const mine = row.member.id === meId;
        const todayState = index >= 0 ? row.states[index] : undefined;
        const ended = leftOn[row.member.id];
        const notes = [
          row.streak ? t("checkins.board.streak", { n: row.streak }) : null,
          todayState && LEFT_TODAY.includes(todayState) ? t("checkins.board.notYet") : null,
          ended ? t("checkins.board.left", { date: formatDay(ended, i18n.language) }) : null,
        ].filter(Boolean);
        return (
          <div key={row.member.id} className={cx(styles.boardRow, mine && styles.mine)}>
            <div className={styles.person}>
              <Avatar
                name={name}
                seed={row.member.avatar_seed}
                ring={
                  todayState === "done"
                    ? "done"
                    : todayState && LEFT_TODAY.includes(todayState)
                      ? "todo"
                      : undefined
                }
              />
              <span className={styles.personText}>
                <span className={styles.personName}>
                  {name}
                  {mine && <StatusPill tone="accent">{t("crew.you")}</StatusPill>}
                </span>
                {notes.length > 0 && <span className={styles.meta}>{notes.join(", ")}</span>}
              </span>
              <span className={styles.score}>
                {fixedDays
                  ? t("checkins.fraction", { done, total: done + missed })
                  : t("checkins.board.doneDays", { n: done })}
              </span>
            </div>
            <DayBars
              states={row.states}
              proofs={board.days.map((d) => row.proof_days.includes(d))}
              label={[
                t("checkins.board.rowLabel", { name, done, missed }),
                row.proof_days.length
                  ? t("checkins.board.withProof", { count: row.proof_days.length })
                  : null,
              ]
                .filter(Boolean)
                .join(", ")}
              onPick={(i) => (board.days[i] ?? "") <= today && onPick(i)}
            />
          </div>
        );
      })}
    </div>
  );
}
