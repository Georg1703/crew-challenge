import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { api, call, type components, type paths } from "@/api";
import { newsKey } from "@/features/notifications";
import type { ProofSubject } from "@/features/proofs";
import type { ReactionSummary } from "@/features/reactions";

export type Comment = components["schemas"]["CommentOut"];
/** A target's comments, and my photos picked for my next one there (drafts only I see). */
export type Thread = components["schemas"]["ThreadOut"];
export type CommentSummary = components["schemas"]["CommentSummaryOut"];
/** What can be commented on, as the API names it ("entry"). */
export type CommentTarget =
  paths["/api/v1/comments/{target}/{target_id}"]["get"]["parameters"]["path"]["target"];

export const MAX_LENGTH = 500;
/** A comment can be deleted in its first minute (the server decides at the edge). */
export const DELETE_MS = 60_000;
/** How often an open thread asks for new comments (only while the page is visible). */
const REFRESH_MS = 5_000;

const commentsKey = ["comments"] as const;
const threadKey = (target: CommentTarget, id: string) => [...commentsKey, target, id] as const;

/** A target's comments, oldest first, and my drafts; refreshed every 5 s while visible. */
export function useThread(target: CommentTarget, id: string) {
  return useQuery({
    queryKey: threadKey(target, id),
    queryFn: () =>
      call(
        api.GET("/api/v1/comments/{target}/{target_id}", {
          params: { path: { target, target_id: id } },
        }),
      ),
    refetchInterval: REFRESH_MS,
  });
}

/** Where photos for my next comment on a target upload (`features/proofs`): photos only. */
export function commentSubject(target: CommentTarget, id: string): ProofSubject {
  return {
    key: `comment:${target}:${id}`,
    start: (body) =>
      call(
        api.POST("/api/v1/comments/{target}/{target_id}/images", {
          params: { path: { target, target_id: id } },
          body,
        }),
      ),
    resume: () => Promise.reject(new Error("Photos are sent whole: nothing to resume.")),
  };
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
      client.setQueryData<Thread>(threadKey(target, id), (thread) => ({
        results: [
          ...(thread?.results ?? []).filter((c) => c.id !== comment.id), // a refresh brought it
          comment,
        ],
        drafts: [], // my photos went with it
      })),
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
      client.setQueryData<Thread>(
        threadKey(target, id),
        (thread) =>
          thread && { ...thread, results: thread.results.filter((c) => c.id !== commentId) },
      ),
  });
}

/** Put a comment's new reactions into the cached thread (its `Reactions` calls it). */
export function usePatchCommentReactions(target: CommentTarget, id: string) {
  const client = useQueryClient();
  return useCallback(
    (commentId: string, reactions: ReactionSummary) => {
      void client.cancelQueries({ queryKey: threadKey(target, id) }); // a refresh would undo it
      client.setQueryData<Thread>(
        threadKey(target, id),
        (thread) =>
          thread && {
            ...thread,
            results: thread.results.map((c) => (c.id === commentId ? { ...c, reactions } : c)),
          },
      );
    },
    [client, target, id],
  );
}

/** Mark a target's comments read, up to now; its news is read with them: the badge asks again. */
export function useMarkRead(target: CommentTarget, id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () =>
      call(
        api.PUT("/api/v1/comments/{target}/{target_id}/read", {
          params: { path: { target, target_id: id } },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: newsKey }),
  });
}
