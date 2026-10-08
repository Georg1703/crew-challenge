import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { CHALLENGE_ICONS } from "@/features/challenges";
import { SHOWN_PROOFS, shownTile } from "@/features/proofs";
import { formatDayLong } from "@/shared/lib/format";
import { FeedCard } from "@/shared/ui";

import type { SpinItem } from "../api";
import { describeFailed } from "../describe";

/** A drawn spin in the crew's journal: who drew which punishment, and how it is going. */
export function SpinFeedCard({
  item,
  time,
  onOpenProof,
  reactions,
}: {
  item: SpinItem;
  /** When, formatted by the journal. */
  time: string;
  onOpenProof: (index: number) => void;
  reactions: ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const who = item.member.display_name;
  const served = item.state === "served";
  const status = served
    ? t("doom.served")
    : item.late
      ? t("doom.late")
      : t("doom.serveBy", { date: formatDayLong(item.serve_by, language) });
  return (
    <FeedCard
      person={{ id: item.member.id, name: who, seed: item.member.avatar_seed }}
      text={t(served ? "doom.feed.served" : "doom.feed.drew", { name: who })}
      challenge={{ icon: CHALLENGE_ICONS[item.challenge.icon], label: item.challenge.title }}
      time={time}
      tone={served ? "success" : "default"}
      highlight={{ value: String(item.punishment.position), text: item.punishment.text }}
      proofs={item.proofs.map((p) => shownTile(p, t, who))}
      onOpenProof={onOpenProof}
      moreLabel={t("feed.more", { count: item.proofs.length - SHOWN_PROOFS })}
      facts={[status, describeFailed(t, item, language)]}
      reactions={reactions}
    />
  );
}
