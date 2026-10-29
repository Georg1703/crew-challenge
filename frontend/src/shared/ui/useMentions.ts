import { useEffect, useState, type RefObject } from "react";

import { ALL, insertMention, mentionQuery, type Person } from "@/shared/lib/mentions";

import { type MentionOption } from "./MentionMenu";

const ROWS = 5;

/**
 * Drives a `MentionMenu` from a text box: while the caret sits after an `@`, the rows are
 * "Everyone" and the crew's other members whose name starts with what was typed (at most five);
 * picking one puts `@Name ` in the text and the caret after it. Picking, or Escape, hides the
 * list until the text changes. Returns the rows and the pick, for the caller's `MentionMenu`.
 */
export function useMentions({
  value,
  onChange,
  box,
  people,
  me,
  everyone,
  maxLength,
}: {
  value: string;
  onChange: (value: string) => void;
  box: RefObject<HTMLTextAreaElement | null>;
  people: (Person & { avatar_seed: string })[];
  /** My member id: not offered. */
  me?: string;
  /** The "Everyone" row's name. */
  everyone: string;
  maxLength?: number;
}) {
  const [hidden, setHidden] = useState<string | null>(null);
  // ponytail: the caret is read when the text changes; moving it alone (arrow keys, a tap) does
  // not redraw the rows. Listen to `selectionchange` if that ever matters.
  const caret = box.current?.selectionStart ?? value.length;
  const typed = mentionQuery(value, caret);

  useEffect(() => {
    const field = box.current;
    if (!field) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setHidden(field.value);
    };
    field.addEventListener("keydown", onKey);
    return () => field.removeEventListener("keydown", onKey);
  }, [box]);

  const query = typed && hidden !== value ? typed.query.toLowerCase() : null;
  const options: MentionOption[] =
    query === null
      ? []
      : [
          ...(ALL.startsWith(query) ? [{ id: ALL, name: everyone, insert: ALL }] : []),
          ...people
            .filter((p) => p.id !== me && p.display_name.toLowerCase().startsWith(query))
            .map((p) => ({ id: p.id, name: p.display_name, seed: p.avatar_seed })),
        ].slice(0, ROWS);

  const pick = (option: MentionOption) => {
    if (!typed) return;
    const next = insertMention(value, typed.start, caret, option.insert ?? option.name);
    if (maxLength !== undefined && next.value.length > maxLength) return;
    setHidden(next.value); // done with this one until more is typed
    onChange(next.value);
    window.requestAnimationFrame(() => {
      box.current?.focus();
      box.current?.setSelectionRange(next.caret, next.caret);
    });
  };

  return { options, pick };
}
