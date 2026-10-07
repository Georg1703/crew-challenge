/**
 * Crew-local calendar dates as the API sends them ("2026-11-01"), worked out without time zones:
 * each one is read as midnight UTC, so adding days never crosses a clock change.
 */

export const DAY_MS = 86_400_000;

/** "2026-11-01" as a Date at midnight UTC. */
export const toDate = (day: string) => new Date(`${day}T00:00:00Z`);

/** A Date (read in UTC) as "2026-11-01". */
const toDay = (date: Date) => date.toISOString().slice(0, 10);

export const addDays = (day: string, days: number) =>
  toDay(new Date(toDate(day).getTime() + days * DAY_MS));

/** Whole days from `a` to `b`. */
export const daysBetween = (a: string, b: string) =>
  Math.round((toDate(b).getTime() - toDate(a).getTime()) / DAY_MS);

/** Monday = 0 ... Sunday = 6. */
export const weekday = (day: string) => (toDate(day).getUTCDay() + 6) % 7;

export const mondayOf = (day: string) => addDays(day, -weekday(day));

/** 1-31. */
export const dayOfMonth = (day: string) => Number(day.slice(8, 10));

/** The first day of the month `offset` months after the month of `day`. */
export function monthStart(day: string, offset = 0): string {
  const date = toDate(day);
  return toDay(new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset, 1)));
}

/** The last day of `length` months (from the 1st), weeks (from a Monday) or days. */
export function periodEnd(kind: "month" | "week" | "day", start: string, length: number): string {
  if (kind === "month") return addDays(monthStart(start, length), -1);
  return addDays(start, (kind === "week" ? 7 * length : length) - 1);
}
