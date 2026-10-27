/**
 * The browser side of Web Push: permission, the subscription in the service worker, and the
 * flags that decide what the Me switch and the prompt show. No network here (`api.ts`).
 */

export type Subscription = { endpoint: string; keys: { p256dh: string; auth: string } };

const FIRST_CHECK_IN_KEY = "checked-in-once";
const PROMPT_DISMISSED_KEY = "push-prompt-dismissed-at";
const DISMISS_FOR_MS = 14 * 24 * 60 * 60 * 1000;

export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function pushPermission(): NotificationPermission {
  return pushSupported() ? Notification.permission : "denied";
}

/** The browser's current subscription, as the API takes it; null when there is none. */
export async function currentSubscription(): Promise<Subscription | null> {
  if (!pushSupported() || Notification.permission !== "granted") return null;
  const registration = await navigator.serviceWorker.ready;
  return asSubscription(await registration.pushManager.getSubscription());
}

/** Ask for permission (after a tap) and subscribe with the server's key; null when refused. */
export async function subscribePush(publicKey: string): Promise<Subscription | null> {
  if (!pushSupported()) return null;
  if ((await Notification.requestPermission()) !== "granted") return null;
  const registration = await navigator.serviceWorker.ready;
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: toKey(publicKey),
    }));
  return asSubscription(subscription);
}

/** Drop the browser's subscription; the endpoint it had, so the server forgets it too. */
export async function unsubscribePush(): Promise<string | null> {
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) return null;
  await subscription.unsubscribe();
  return subscription.endpoint;
}

function asSubscription(subscription: PushSubscription | null): Subscription | null {
  const json = subscription?.toJSON();
  const { p256dh, auth } = json?.keys ?? {};
  return json?.endpoint && p256dh && auth
    ? { endpoint: json.endpoint, keys: { p256dh, auth } }
    : null;
}

/** A VAPID public key (base64url) as the bytes `pushManager.subscribe` takes. */
export function toKey(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = (base64url + "=".repeat((4 - (base64url.length % 4)) % 4))
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  const raw = atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

// --- the prompt's memory (this device only) --------------------------------------------------

/** A check-in was posted on this device: from now on the prompt may show (never on first load). */
export function noteCheckIn(): void {
  try {
    localStorage.setItem(FIRST_CHECK_IN_KEY, "1");
  } catch {
    // No storage: no prompt, the Me switch is there.
  }
}

export function checkedInOnce(): boolean {
  try {
    return localStorage.getItem(FIRST_CHECK_IN_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissPrompt(): void {
  try {
    localStorage.setItem(PROMPT_DISMISSED_KEY, String(Date.now()));
  } catch {
    // Not critical.
  }
}

export function promptDismissed(): boolean {
  try {
    const at = Number(localStorage.getItem(PROMPT_DISMISSED_KEY));
    return Boolean(at) && Date.now() - at < DISMISS_FOR_MS;
  } catch {
    return false;
  }
}
