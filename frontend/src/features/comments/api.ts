import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { api, call, type components, type paths } from "@/api";
import type { ReactionSummary } from "@/features/reactions";

export type Comment = components["schemas"]["CommentOut"];
export type CommentSummary = components["schemas"]["CommentSummaryOut"];
/** What can be commented on, as the API names it ("entry"). */
export type CommentTarget =
  paths["/api/v1/comments/{target}/{target_id}"]["get"]["parameters"]["path"]["target"];

/** A comment of level 5 takes no reply. */
export const MAX_LEVEL = 5;
export const MAX_LENGTH = 500;
/** A comment can be deleted in its first minute (the server decides at the edge). */
export const DELETE_MS = 60_000;
/** How often an open thread asks for new comments (only while the page is visible). */
const REFRESH_MS = 5_000;

const threadKey = (target: CommentTarget, id: string) => ["comments", target, id] as const;

/** A target's comments, oldest first, refreshed every 5 s while the page is visible. */
export function useThread(target: CommentTarget, id: string) {
  return useQuery({
    queryKey: threadKey(target, id),
    queryFn: () =>
      call(
        api.GET("/api/v1/comments/{target}/{target_id}", {
          params: { path: { target, target_id: id } },
        }),
      ).then((thread) => thread.results),
    refetchInterval: REFRESH_MS,
  });
}

/** Comment on the target, or reply (`parent_id`); the thread shows it once the server has it. */
export function useAddComment(target: CommentTarget, id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { text: string; parent_id?: string }) =>
      call(
        api.POST("/api/v1/comments/{target}/{target_id}", {
          params: { path: { target, target_id: id } },
          body,
        }),
      ),
    onSuccess: (comment) =>
      client.setQueryData<Comment[]>(threadKey(target, id), (thread) => [
        ...(thread ?? []).filter((c) => c.id !== comment.id), // a refresh may have brought it
        comment,
      ]),
  });
}

/** Delete my comment; it leaves the thread when the server agrees. */
export function useDeleteComment(target: CommentTarget, id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) =>
      call(
        api.DELETE("/api/v1/comments/{comment_id}", {
          params: { path: { comment_id: commentId } },
        }),
      ),
    onSuccess: (_, commentId) =>
      client.setQueryData<Comment[]>(threadKey(target, id), (thread) =>
        thread?.filter((c) => c.id !== commentId),
      ),
  });
}

/** Put a comment's new reactions into the cached thread (its `Reactions` calls it). */
export function usePatchCommentReactions(target: CommentTarget, id: string) {
  const client = useQueryClient();
  return useCallback(
    (commentId: string, reactions: ReactionSummary) => {
      void client.cancelQueries({ queryKey: threadKey(target, id) }); // a refresh would undo it
      client.setQueryData<Comment[]>(threadKey(target, id), (thread) =>
        thread?.map((c) => (c.id === commentId ? { ...c, reactions } : c)),
      );
    },
    [client, target, id],
  );
}
