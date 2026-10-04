/** CSRF token handling for Django's session auth. See docs/architecture/api-conventions.md. */

const COOKIE = "csrftoken";

export function readCsrfCookie(): string | null {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${COOKIE}=`));
  return match ? decodeURIComponent(match.slice(COOKIE.length + 1)) : null;
}

let pending: Promise<void> | null = null;

/** Make sure the csrftoken cookie exists (fetches /api/v1/auth/csrf once if needed). */
export async function ensureCsrfCookie(): Promise<string> {
  const existing = readCsrfCookie();
  if (existing) return existing;
  pending ??= fetch("/api/v1/auth/csrf", { credentials: "same-origin" }).then(() => undefined);
  try {
    await pending;
  } finally {
    pending = null;
  }
  return readCsrfCookie() ?? "";
}

export const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
