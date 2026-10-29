/**
 * `@Name` in a comment: the text stays plain, a mention is `@` followed by a crew member's
 * display name as it is written, or `@all` for the whole crew. The same rules as the server's
 * `apps/crews/mentions.py`: names tried longest first, matched regardless of case, ending where
 * the text ends or before a character that cannot continue a name. `docs/plans/mentions.md`.
 */

export const ALL = "all";

export type Person = { id: string; display_name: string };

/** A piece of a text: plain, a member's mention, or `@all`. */
export type Segment = { text: string; member?: Person; all?: boolean };

// An `@` that starts a word: at the start, or after a space or punctuation (not in an email).
const AT = /(?<![\p{L}\p{N}_])@/gu;
const NAME_CHAR = /[\p{L}\p{N}]/u;

const starts = (rest: string, name: string) =>
  rest.startsWith(name) &&
  (rest.length === name.length || !NAME_CHAR.test(rest[name.length] ?? ""));

export function findMentions(text: string, people: Person[]): Segment[] {
  const sorted = [...people].sort((a, b) => b.display_name.length - a.display_name.length);
  const folded = text.toLowerCase();
  const out: Segment[] = [];
  let from = 0;
  for (const hit of text.matchAll(AT)) {
    const at = hit.index;
    const rest = folded.slice(at + 1);
    let found: Segment | null = null;
    if (starts(rest, ALL)) found = { text: text.slice(at, at + 1 + ALL.length), all: true };
    else {
      const member = sorted.find((p) => starts(rest, p.display_name.toLowerCase()));
      if (member) found = { text: text.slice(at, at + 1 + member.display_name.length), member };
    }
    if (!found || at < from) continue;
    if (at > from) out.push({ text: text.slice(from, at) });
    out.push(found);
    from = at + found.text.length;
  }
  if (from < text.length) out.push({ text: text.slice(from) });
  return out;
}

/** The mention being typed: the `@` under the caret and what follows it, or null. */
export function mentionQuery(
  value: string,
  caret: number,
): { start: number; query: string } | null {
  const before = value.slice(0, caret);
  const start = before.lastIndexOf("@");
  if (start < 0 || (start > 0 && /[\p{L}\p{N}_]/u.test(before[start - 1] ?? ""))) return null;
  const query = before.slice(start + 1);
  return query.includes("\n") ? null : { start, query };
}

/** `@name ` in place of what was typed after the `@`; the caret after it. */
export function insertMention(value: string, start: number, caret: number, name: string) {
  const mention = `@${name} `;
  return {
    value: value.slice(0, start) + mention + value.slice(caret),
    caret: start + mention.length,
  };
}
