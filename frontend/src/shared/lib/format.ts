/** Format an instant for display in the crew's time zone (not the phone's). */
export function formatDateTime(iso: string, language: string, timeZone: string): string {
  return new Intl.DateTimeFormat(language, {
    timeZone,
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** A calendar date ("12 octombrie"). Without `timeZone` it uses the phone's zone. */
export function formatDate(iso: string, language: string, timeZone?: string): string {
  return new Intl.DateTimeFormat(language, { timeZone, day: "numeric", month: "long" }).format(
    new Date(iso),
  );
}

/** "Ana, Bogdan și Cristina" in the UI language. */
export function formatList(items: string[], language: string): string {
  return new Intl.ListFormat(language, { style: "long", type: "conjunction" }).format(items);
}

/** A crew-local calendar date from the API ("2026-11-01") as "1 noiembrie". No time zone shift. */
export function formatDay(day: string, language: string): string {
  return new Intl.DateTimeFormat(language, {
    timeZone: "UTC",
    day: "numeric",
    month: "long",
  }).format(new Date(`${day}T00:00:00Z`));
}

/** The month of a crew-local date ("2026-11-01") as "noiembrie". */
export function monthName(day: string, language: string): string {
  return new Intl.DateTimeFormat(language, { timeZone: "UTC", month: "long" }).format(
    new Date(`${day}T00:00:00Z`),
  );
}

/** Today's date in a time zone as "2026-10-05" (the crew's day, not the phone's). */
export function todayIn(timeZone: string, now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(now);
}

/** "Noiembrie 2026" for a crew-local date (capitalized: it is used as a heading or an option). */
export function monthAndYear(day: string, language: string): string {
  const text = new Intl.DateTimeFormat(language, {
    timeZone: "UTC",
    month: "long",
    year: "numeric",
  }).format(new Date(`${day}T00:00:00Z`));
  return text.charAt(0).toLocaleUpperCase(language) + text.slice(1);
}

/** A number with at most two decimals, in the UI language: "12,5". */
export function formatNumber(value: number, language: string): string {
  return new Intl.NumberFormat(language, { maximumFractionDigits: 2 }).format(value);
}

const MINUTE_MS = 60_000;

/**
 * When something happened, as a feed says it: "now", "5 min ago" within the hour, "21:40" today,
 * "yesterday 21:40", else "5 October, 21:40". Days follow the crew's time zone.
 */
export function formatWhen(
  iso: string,
  language: string,
  timeZone: string,
  now: Date = new Date(),
): string {
  const then = new Date(iso);
  const minutes = Math.floor((now.getTime() - then.getTime()) / MINUTE_MS);
  const relative = new Intl.RelativeTimeFormat(language, { numeric: "auto", style: "short" });
  if (minutes < 1) return relative.format(0, "second");
  if (minutes < 60) return relative.format(-minutes, "minute");
  const time = new Intl.DateTimeFormat(language, {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
  }).format(then);
  const days = Math.round(
    (Date.parse(todayIn(timeZone, now)) - Date.parse(todayIn(timeZone, then))) /
      (24 * 60 * MINUTE_MS),
  );
  if (days === 0) return time;
  if (days === 1) return `${relative.format(-1, "day")} ${time}`;
  return formatDateTime(iso, language, timeZone);
}

/** A crew-local date with its weekday, for a heading: "Luni, 5 octombrie". */
export function formatDayLong(day: string, language: string): string {
  const text = new Intl.DateTimeFormat(language, {
    timeZone: "UTC",
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(`${day}T00:00:00Z`));
  return text.charAt(0).toLocaleUpperCase(language) + text.slice(1);
}
