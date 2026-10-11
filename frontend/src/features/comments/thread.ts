import { DELETE_MS, type Comment } from "./api";

/** Whether `me` may delete it now: mine, nobody has replied, in its first minute (the server
 * decides at the edge). Asked when its menu opens. */
export function deletable(
  comment: Comment,
  hasReplies: boolean,
  me: string | undefined,
  now = Date.now(),
) {
  return (
    comment.member_id === me && !hasReplies && now - Date.parse(comment.created_at) < DELETE_MS
  );
}
