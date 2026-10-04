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
