import type { SpinItem } from "@/features/doom";

import type { FeedItem, JournalEntry } from "./api";

export type JournalCard =
  | { kind: "item"; key: string; item: FeedItem }
  /** Plain check-ins of one challenge on one day, said in one card. */
  | { kind: "group"; key: string; items: FeedItem[] }
  /** Everyone finished everything due that day. */
  | { kind: "crew"; key: string }
  /** A drawn spin (Wheel of Doom), at the time of its latest activity. */
  | { kind: "spin"; key: string; spin: SpinItem; at: string };

export interface JournalDay {
  day: string;
  summary: FeedItem["day_summary"];
  cards: JournalCard[];
}

/** A check-in with nothing to show but the fact: no proofs, no number, no milestone. */
function plain(item: FeedItem): boolean {
  return (
    item.proofs.length === 0 && item.milestone === null && item.challenge.measure !== "quantity"
  );
}

/**
 * The crew's journal, day by day: one entry per day (latest day first), its cards in the order
 * things happened (latest first), plain check-ins of one challenge gathered where the latest of
 * them sits, and the crew's whole day on top when everyone finished. Spins are cards of their own.
 */
export function journal(entries: JournalEntry[]): JournalDay[] {
  const days = new Map<string, JournalDay>();
  const groups = new Map<string, Extract<JournalCard, { kind: "group" }>>();
  const dayOf = (day: string, summary: FeedItem["day_summary"]) => {
    let entry = days.get(day);
    if (!entry) {
      entry = { day, summary, cards: [] };
      if (summary.crew_done) entry.cards.push({ kind: "crew", key: `crew-${day}` });
      days.set(day, entry);
    }
    return entry;
  };
  for (const { check_in: item, spin, activity_at: at } of entries) {
    if (spin) {
      dayOf(spin.day, spin.day_summary).cards.push({
        kind: "spin",
        key: `spin-${spin.id}`,
        spin,
        at,
      });
      continue;
    }
    if (!item) continue;
    const entry = dayOf(item.day, item.day_summary);
    if (!plain(item)) {
      entry.cards.push({ kind: "item", key: item.id, item });
      continue;
    }
    const groupKey = `${item.day}-${item.challenge.id}`;
    const group = groups.get(groupKey);
    if (group) {
      group.items.push(item);
    } else {
      const card = { kind: "group" as const, key: `group-${item.id}`, items: [item] };
      groups.set(groupKey, card);
      entry.cards.push(card);
    }
  }
  return [...days.values()].sort((a, b) => (a.day < b.day ? 1 : a.day > b.day ? -1 : 0));
}
