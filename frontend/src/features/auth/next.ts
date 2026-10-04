/**
 * Where to go after logging in. Only paths inside this app are allowed ("/join/abc"), never
 * another site ("https://evil.example", "//evil.example"), so a link cannot send people away.
 */
export function safeNext(value: string | null): string {
  if (!value?.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/";
  return value;
}
