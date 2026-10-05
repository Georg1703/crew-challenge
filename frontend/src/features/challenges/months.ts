/** Months an admin can schedule a challenge for, worked out on crew-local dates ("2026-10-05"). */

export type MonthOption = {
  /** First day of the month, sent to the API. */
  periodStart: string;
  /** The first day that counts: tomorrow for the current month, else the 1st. */
  startsOn: string;
};

const iso = (date: Date) => date.toISOString().slice(0, 10);
const utc = (day: string) => new Date(`${day}T00:00:00Z`);

/** First day of the month `offset` months after the month of `day`. */
export function monthStart(day: string, offset = 0): string {
  const date = utc(day);
  return iso(new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset, 1)));
}

/**
 * The rest of this month (when at least tomorrow is still in it) and the next `ahead` months.
 * The server checks the same rules again.
 */
export function monthOptions(today: string, ahead = 3): MonthOption[] {
  const tomorrow = utc(today);
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  const options: MonthOption[] = [];
  if (monthStart(iso(tomorrow)) === monthStart(today)) {
    options.push({ periodStart: monthStart(today), startsOn: iso(tomorrow) });
  }
  for (let offset = 1; offset <= ahead; offset += 1) {
    const first = monthStart(today, offset);
    options.push({ periodStart: first, startsOn: first });
  }
  return options;
}
