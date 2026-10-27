import type { ComponentProps, ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "@/api";
import { CHALLENGE_ICONS } from "@/features/challenges";
import { SHOWN_PROOFS, shownTile, type Proof } from "@/features/proofs";
import { formatDayLong } from "@/shared/lib/format";
import { FeedCard, TruncatedText } from "@/shared/ui";

import { describeFailed } from "../describe";

type Person = components["schemas"]["PersonOut"];
type Challenge = components["schemas"]["ChallengeBriefOut"];
type Drawn = components["schemas"]["SpinFactsOut"];

/**
 * A spin in the crew's journal, as one of its two cards, each as it was then: who drew which
 * punishment, what failed and by when to serve it (`drawn`), or who served it, with the photos
 * and videos (`drawn` is null).
 */
export function SpinFeedCard({
  member,
  challenge,
  punishment,
  drawn,
  proofs,
  time,
  onOpenProof,
  reactions,
  comments,
}: {
  member: Person;
  challenge: Challenge;
  punishment: string;
  drawn: Drawn | null;
  proofs: Proof[];
  /** When, formatted by the journal. */
  time: string;
  onOpenProof: (index: number) => void;
  reactions: ReactNode;
  /** The link to its comments (see `FeedCard`). */
  comments?: ComponentProps<typeof FeedCard>["comments"];
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const who = member.display_name;
  const facts = drawn
    ? [
        ...(drawn.serve_by
          ? [t("doom.serveBy", { date: formatDayLong(drawn.serve_by, language) })]
          : []),
        describeFailed(t, { ...drawn, challenge }, language),
      ]
    : undefined;
  return (
    <FeedCard
      person={{
        id: member.id,
        name: who,
        seed: member.avatar_seed,
        to: `/crew/members/${member.id}`,
      }}
      text={t(drawn ? "doom.feed.drew" : "doom.feed.served", { name: who })}
      challenge={{ icon: CHALLENGE_ICONS[challenge.icon], label: challenge.title }}
      time={time}
      tone={drawn ? "default" : "success"}
      highlight={{ text: <TruncatedText text={punishment} /> }}
      proofs={proofs.map((p) => shownTile(p, t, who))}
      onOpenProof={onOpenProof}
      moreLabel={t("feed.more", { count: proofs.length - SHOWN_PROOFS })}
      facts={facts}
      reactions={reactions}
      comments={comments}
    />
  );
}
