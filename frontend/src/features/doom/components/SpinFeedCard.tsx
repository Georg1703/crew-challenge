import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { CHALLENGE_ICONS } from "@/features/challenges";
import { SHOWN_PROOFS, shownTile } from "@/features/proofs";
import { formatDayLong } from "@/shared/lib/format";
import { FeedCard } from "@/shared/ui";

import type { SpinItem } from "../api";
import { describeFailed } from "../describe";

/**
 * A spin in the crew's journal, as one of two cards: who drew which punishment and by when to
 * serve it (it stays as it was drawn), or, once served, who served it, with the proofs.
 */
export function SpinFeedCard({
  item,
  served,
  time,
  onOpenProof,
  reactions,
}: {
  item: SpinItem;
  /** The served card, else the drawn one. */
  served: boolean;
  /** When, formatted by the journal. */
  time: string;
  onOpenProof: (index: number) => void;
  reactions: ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const who = item.member.display_name;
  const failed = describeFailed(t, item, language);
  return (
    <FeedCard
      person={{ id: item.member.id, name: who, seed: item.member.avatar_seed }}
      text={t(served ? "doom.feed.served" : "doom.feed.drew", { name: who })}
      challenge={{ icon: CHALLENGE_ICONS[item.challenge.icon], label: item.challenge.title }}
      time={time}
      tone={served ? "success" : "default"}
      highlight={{ text: item.punishment.text }}
      proofs={item.proofs.map((p) => shownTile(p, t, who))}
      onOpenProof={onOpenProof}
      moreLabel={t("feed.more", { count: item.proofs.length - SHOWN_PROOFS })}
      facts={
        served
          ? [failed]
          : [t("doom.serveBy", { date: formatDayLong(item.serve_by, language) }), failed]
      }
      reactions={reactions}
    />
  );
}
