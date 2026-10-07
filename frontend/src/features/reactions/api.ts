import { useMutation } from "@tanstack/react-query";

import { api, call, type components, type paths } from "@/api";

export type ReactionSummary = components["schemas"]["ReactionSummaryOut"];
/** What can be reacted to, as the API names it ("check_in"); grows as the backend registers more. */
export type ReactionTarget =
  paths["/api/v1/reactions/{target}/{target_id}"]["put"]["parameters"]["path"]["target"];

/** The quick row: the same six for everyone in this version. */
export const QUICK_REACTIONS = [
  "\u{1F44D}", // thumbs up
  "\u{1F525}", // fire
  "\u{1F44F}", // clapping hands
  "\u{1F4AA}", // flexed biceps
  "\u{1F602}", // face with tears of joy
  "❤️", // red heart
];

/**
 * A summary with `me` reacting with `emoji` (or taking it back with null), as the server will
 * answer: one reaction per person, a new emoji goes last, empty groups go away.
 */
export function applyReaction(
  summary: ReactionSummary,
  me: string,
  emoji: string | null,
): ReactionSummary {
  const groups = summary.groups
    .map((group) => ({ ...group, member_ids: group.member_ids.filter((id) => id !== me) }))
    .filter((group) => group.member_ids.length > 0);
  if (emoji) {
    const existing = groups.find((group) => group.emoji === emoji);
    if (existing) existing.member_ids.push(me);
    else groups.push({ emoji, member_ids: [me] });
  }
  return { groups, mine: emoji };
}

/**
 * React to one target, optimistically: `onChange` gets the expected summary at once, then the
 * server's, or the old one back on error. `onSaved` gets the server's answer only, for the owner
 * of the data (a feed, a page) to keep in its own cache; this hook knows nothing about other
 * features' queries.
 */
export function useReact({
  target,
  id,
  me,
  summary,
  onChange,
  onSaved,
  onError,
}: {
  target: ReactionTarget;
  id: string;
  me: string;
  summary: ReactionSummary;
  onChange: (summary: ReactionSummary) => void;
  onSaved: (summary: ReactionSummary) => void;
  onError: (error: unknown) => void;
}) {
  return useMutation({
    mutationFn: (emoji: string | null) => {
      const params = { path: { target, target_id: id } };
      return call(
        emoji
          ? api.PUT("/api/v1/reactions/{target}/{target_id}", { params, body: { emoji } })
          : api.DELETE("/api/v1/reactions/{target}/{target_id}", { params }),
      );
    },
    onMutate: (emoji) => {
      const before = summary;
      onChange(applyReaction(before, me, emoji));
      return { before };
    },
    onSuccess: (answer) => {
      onChange(answer);
      onSaved(answer);
    },
    onError: (error, _emoji, context) => {
      if (context) onChange(context.before);
      onError(error);
    },
  });
}
