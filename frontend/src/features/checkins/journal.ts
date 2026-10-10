import type { JournalEntry, JournalPage } from "./api";

export interface JournalDay {
  day: string;
  /** Check-ins (one per person and challenge) and photos and videos posted that day. */
  summary: { check_ins: number; proofs: number };
  cards: JournalEntry[];
}

/**
 * The crew's journal, day by day: one entry per day (latest day first), its cards in the order
 * they were posted (latest first). Each card is a post as it was made: nothing is merged.
 */
export function journal(pages: JournalPage[]): JournalDay[] {
  const counts = new Map(pages.flatMap((page) => page.days.map((d) => [d.day, d] as const)));
  const days = new Map<string, JournalDay>();
  for (const card of pages.flatMap((page) => page.results)) {
    let entry = days.get(card.day);
    if (!entry) {
      const summary = counts.get(card.day) ?? { check_ins: 0, proofs: 0 };
      entry = { day: card.day, summary, cards: [] };
      days.set(card.day, entry);
    }
    entry.cards.push(card);
  }
  return [...days.values()].sort((a, b) => (a.day < b.day ? 1 : a.day > b.day ? -1 : 0));
}
