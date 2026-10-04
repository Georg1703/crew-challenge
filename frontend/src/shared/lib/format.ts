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
