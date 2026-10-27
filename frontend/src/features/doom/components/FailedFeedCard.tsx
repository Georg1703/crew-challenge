import type { ComponentProps, ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "@/api";
import { CHALLENGE_ICONS } from "@/features/challenges";
import { FeedCard } from "@/shared/ui";

import { describeFailed } from "../describe";

type Person = components["schemas"]["PersonOut"];
type Challenge = components["schemas"]["ChallengeBriefOut"];
type Failed = components["schemas"]["FailedFactsOut"];

/**
 * A failed window in the crew's journal, written as its spins opened: who fell short, what
 * failed and how many spins they owe, as it was then.
 */
export function FailedFeedCard({
  member,
  challenge,
  failed,
  time,
  reactions,
  comments,
}: {
  member: Person;
  challenge: Challenge;
  failed: Failed;
  /** When, formatted by the journal. */
  time: string;
  reactions: ReactNode;
  /** The link to its comments (see `FeedCard`). */
  comments?: ComponentProps<typeof FeedCard>["comments"];
}) {
  const { t, i18n } = useTranslation();
  return (
    <FeedCard
      person={{
        id: member.id,
        name: member.display_name,
        seed: member.avatar_seed,
        to: `/crew/members/${member.id}`,
      }}
      text={t("doom.feed.failed", { name: member.display_name })}
      challenge={{ icon: CHALLENGE_ICONS[challenge.icon], label: challenge.title }}
      time={time}
      facts={[
        describeFailed(t, { ...failed, challenge }, i18n.language),
        t("doom.feed.owes", { count: failed.spins }),
      ]}
      reactions={reactions}
      comments={comments}
    />
  );
}
