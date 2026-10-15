import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { CHALLENGE_ICONS } from "@/features/challenges";
import { FailedFeedCard, SpinFeedCard } from "@/features/doom";
import { SHOWN_PROOFS, shownTile, viewerItem } from "@/features/proofs";
import { Reactions } from "@/features/reactions";
import { formatNumber, formatWhen, todayIn } from "@/shared/lib/format";
import { FeedCard, type ViewerItem } from "@/shared/ui";

import { usePatchJournalReactions, type JournalEntry } from "../api";

type Person = NonNullable<JournalEntry["member"]>;

const person = (member: Person) => ({
  id: member.id,
  name: member.display_name,
  seed: member.avatar_seed,
});

/**
 * One card of the crew's journal, drawn from what it said when it was posted: a check-in, a "+N",
 * photos added later, a failed window, a spin drawn or served, or the crew's day; with its
 * reactions and, with `withComments`, the link to its comments. The feed and the card's own page
 * draw it the same.
 */
export function JournalCard({
  entry,
  members,
  timeZone,
  onOpenProofs,
  withComments = false,
}: {
  entry: JournalEntry;
  members: Member[];
  timeZone: string;
  /** A photo or video was tapped: the viewer opens on `index` of `items`. */
  onOpenProofs: (items: ViewerItem[], index: number) => void;
  withComments?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const patchReactions = usePatchJournalReactions();
  const time = formatWhen(entry.at, language, timeZone);
  const opener = (caption: string) => (index: number) =>
    onOpenProofs(
      entry.proofs.map((p) => viewerItem(p, caption)),
      index,
    );
  const reactions = (
    <Reactions
      target="entry"
      id={entry.id}
      summary={entry.reactions}
      people={members}
      onChange={(summary) => patchReactions(entry.id, summary)}
    />
  );
  const comments = withComments
    ? {
        to: `/crew/cards/${entry.id}`,
        text:
          entry.comments.count > 0
            ? t("comments.count", { count: entry.comments.count })
            : t("comments.comment"),
        people: entry.comments.member_ids
          .map((id) => members.find((m) => m.id === id))
          .filter((m): m is Member => m !== undefined)
          .map(person),
        peopleLabel: t("comments.writers"),
        unread:
          entry.comments.unread > 0
            ? t("comments.unread", { count: entry.comments.unread })
            : undefined,
      }
    : undefined;

  if (entry.crew_day) {
    const due = new Set(entry.crew_day.members);
    return (
      <FeedCard
        tone="success"
        people={{
          members: members.filter((m) => due.has(m.id)).map(person),
          label: t("crew.journal.crewDayLabel"),
        }}
        text={t("crew.journal.crewDay")}
        time={time}
        reactions={reactions}
        comments={comments}
      />
    );
  }
  const { member, challenge } = entry;
  if (!member || !challenge) return null;
  if (entry.failed) {
    return (
      <FailedFeedCard
        member={member}
        challenge={challenge}
        failed={entry.failed}
        time={time}
        reactions={reactions}
        comments={comments}
      />
    );
  }
  const who = member.display_name;
  const punishment = (entry.spin ?? entry.served)?.punishment.text;
  if (punishment !== undefined) {
    return (
      <SpinFeedCard
        member={member}
        challenge={challenge}
        punishment={punishment}
        drawn={entry.spin}
        proofs={entry.proofs}
        time={time}
        onOpenProof={opener(`${who}, ${punishment}`)}
        reactions={reactions}
        comments={comments}
      />
    );
  }
  const facts = entry.check_in;
  if (!facts) return null;
  const unit = challenge.unit;
  const milestone = facts.milestone ?? undefined;
  const alone = milestone !== undefined && entry.proofs.length === 0;
  const total = facts.total ?? 0;
  const text =
    facts.action === "files"
      ? t("crew.journal.files", { name: who, count: facts.proofs })
      : alone
        ? t("crew.journal.milestone", { name: who })
        : t(
            facts.action === "amount"
              ? "crew.journal.added"
              : challenge.measure === "abstain"
                ? "crew.journal.held"
                : "crew.journal.checked",
            { name: who },
          );
  return (
    <FeedCard
      person={person(member)}
      text={text}
      challenge={{ icon: CHALLENGE_ICONS[challenge.icon], label: challenge.title }}
      time={time}
      tone={alone ? "success" : "default"}
      highlight={
        alone
          ? { value: String(milestone), text: t("crew.journal.inARow", { count: milestone }) }
          : undefined
      }
      amount={
        facts.action === "amount"
          ? {
              value: `+${formatNumber(facts.amount ?? 0, language)} ${unit}`.trim(),
              detail: t(
                entry.day === todayIn(timeZone)
                  ? "crew.journal.todayTotal"
                  : "crew.journal.dayTotal",
                { total: formatNumber(total, language) },
              ),
              progress:
                facts.target !== null
                  ? {
                      value: total,
                      max: facts.target,
                      label: t("crew.journal.ofTarget", {
                        total: formatNumber(total, language),
                        target: formatNumber(facts.target, language),
                        unit,
                      }),
                    }
                  : undefined,
            }
          : undefined
      }
      proofs={entry.proofs.map((p) => shownTile(p, t, who))}
      onOpenProof={opener(`${who}, ${challenge.title}`)}
      moreLabel={t("feed.more", { count: entry.proofs.length - SHOWN_PROOFS })}
      facts={
        milestone !== undefined && !alone
          ? [`${milestone} ${t("crew.journal.inARow", { count: milestone })}`]
          : facts.streak !== null && facts.streak > 1
            ? [t("crew.journal.streak", { count: facts.streak })]
            : []
      }
      reactions={reactions}
      comments={comments}
    />
  );
}
