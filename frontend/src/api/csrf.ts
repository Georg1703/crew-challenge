/** CSRF token handling for Django's session auth. See docs/architecture/api-conventions.md. */

const COOKIE = "crew_csrftoken"; // CSRF_COOKIE_NAME in backend settings

export function readCsrfCookie(): string | null {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${COOKIE}=`));
  return match ? decodeURIComponent(match.slice(COOKIE.length + 1)) : null;
}

let pending: Promise<void> | null = null;

/** Make sure the crew_csrftoken cookie exists (fetches /api/v1/auth/csrf once if needed). */
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
