/**
 * When you last looked at each member's proofs, per crew, on this device only (localStorage).
 * Opening a member's page or one of their proofs marks them seen. Blocked storage means no
 * badge and nothing else changes.
 */
import { useSyncExternalStore } from "react";

import type { FeedItem } from "@/features/checkins";

const KEY = "crew-seen";

type Seen = Record<string, Record<string, string>>; // crew id -> member id -> ISO instant

const listeners = new Set<() => void>();
let snapshot = 0;

function read(): Seen {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? (parsed as Seen) : {};
  } catch {
    return {};
  }
}

export function seenAt(crewId: string, memberId: string): string | null {
  return read()[crewId]?.[memberId] ?? null;
}

export function markSeen(crewId: string, memberId: string, at: Date = new Date()): void {
  try {
    const all = read();
    all[crewId] = { ...all[crewId], [memberId]: at.toISOString() };
    localStorage.setItem(KEY, JSON.stringify(all));
  } catch {
    return; // no storage: no badge
  }
  snapshot += 1;
  listeners.forEach((listener) => listener());
}

/** Re-renders when anyone is marked seen. */
export function useSeenVersion(): number {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => snapshot,
  );
}

/**
 * New proofs per member in the loaded feed: added after you last looked, or after `since` (a
 * day ago, say) when you never have. Your own never count.
 */
export function freshCounts(
  items: FeedItem[],
  crewId: string,
  meId: string | undefined,
  since: Date,
): Record<string, number> {
  const all = read()[crewId] ?? {};
  const counts: Record<string, number> = {};
  for (const item of items) {
    const id = item.member.id;
    if (id === meId) continue;
    const seen = all[id];
    const after = seen ? Date.parse(seen) : since.getTime();
    const fresh = item.proofs.filter((p) => Date.parse(p.created_at) > after).length;
    if (fresh > 0) counts[id] = (counts[id] ?? 0) + fresh;
  }
  return counts;
}
