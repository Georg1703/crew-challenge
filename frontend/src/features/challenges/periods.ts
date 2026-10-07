/** When an admin can start a challenge, worked out on crew-local dates ("2026-10-05"). */
import { addDays, mondayOf, monthStart, periodEnd } from "@/shared/lib/dates";

import type { Challenge } from "./api";

export type StartOption = {
  /** The period's first day, sent to the API. */
  periodStart: string;
  /** The first day that counts: tomorrow while the period is under way. */
  startsOn: string;
  endsOn: string;
};

const MONTHS_SHOWN = 3;
const WEEKS_SHOWN = 8;

/**
 * The month or week under way (while tomorrow is still in its period) and the next few. A number
 * of days starts on any date from tomorrow, picked in a date field: no options. The server checks
 * the same rules again.
 */
export function startOptions(
  kind: Challenge["period_kind"],
  length: number,
  today: string,
): StartOption[] {
  if (kind === "day") return [];
  const current = kind === "month" ? monthStart(today) : mondayOf(today);
  const nth = (n: number) => (kind === "month" ? monthStart(today, n) : addDays(current, 7 * n));
  const tomorrow = addDays(today, 1);
  const options: StartOption[] = [];
  const currentEnd = periodEnd(kind, current, length);
  if (tomorrow <= currentEnd) {
    options.push({ periodStart: current, startsOn: tomorrow, endsOn: currentEnd });
  }
  for (let n = 1; n <= (kind === "month" ? MONTHS_SHOWN : WEEKS_SHOWN); n += 1) {
    const first = nth(n);
    options.push({ periodStart: first, startsOn: first, endsOn: periodEnd(kind, first, length) });
  }
  return options;
}
