import type { FeedItem } from "./api";

export type JournalCard =
  | { kind: "item"; key: string; item: FeedItem }
  /** Plain check-ins of one challenge on one day, said in one card. */
  | { kind: "group"; key: string; items: FeedItem[] }
  /** Everyone finished everything due that day. */
  | { kind: "crew"; key: string };

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
 * The feed as the crew's journal: one entry per day (latest day first), its cards in the order
 * things happened (latest first), plain check-ins of one challenge gathered where the latest of
 * them sits, and the crew's whole day on top when everyone finished.
 */
export function journal(items: FeedItem[]): JournalDay[] {
  const days = new Map<string, JournalDay>();
  const groups = new Map<string, Extract<JournalCard, { kind: "group" }>>();
  for (const item of items) {
    let entry = days.get(item.day);
    if (!entry) {
      entry = { day: item.day, summary: item.day_summary, cards: [] };
      if (item.day_summary.crew_done) entry.cards.push({ kind: "crew", key: `crew-${item.day}` });
      days.set(item.day, entry);
    }
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
