/**
 * Where to go after logging in. Only paths inside this app are allowed ("/join/abc"), never
 * another site ("https://evil.example", "//evil.example", "/%09/evil.example"), so a link cannot
 * send people away.
 */
export function safeNext(value: string | null, origin = globalThis.location.origin): string {
  // Browsers drop tabs and newlines inside URLs, which turns "/\t/evil" into "//evil".
  if (!value?.startsWith("/") || /[\s\\]/.test(value)) return "/";
  try {
    const target = new URL(value, origin);
    if (target.origin !== origin) return "/";
    return target.pathname + target.search + target.hash;
  } catch {
    return "/";
  }
}
