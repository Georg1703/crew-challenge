import { Fragment, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { CHALLENGE_ICONS } from "@/features/challenges";
import { SpinFeedCard } from "@/features/doom";
import { SHOWN_PROOFS, shownTile, viewerItem } from "@/features/proofs";
import { Reactions } from "@/features/reactions";
import { errorMessage } from "@/i18n/errors";
import { addDays } from "@/shared/lib/dates";
import { formatDayLong, formatNumber, formatWhen, todayIn } from "@/shared/lib/format";
import {
  Banner,
  Button,
  DayDivider,
  FeedCard,
  ProofViewer,
  Skeleton,
  Stack,
  type ViewerItem,
} from "@/shared/ui";

import { useJournal, usePatchJournalReactions, type JournalEntry } from "../api";
import styles from "../checkins.module.css";
import { journal, type JournalDay } from "../journal";

type T = ReturnType<typeof useTranslation>["t"];
type Person = NonNullable<JournalEntry["member"]>;

const person = (member: Person) => ({
  id: member.id,
  name: member.display_name,
  seed: member.avatar_seed,
});

/** "Today", "Yesterday", else "Monday, 5 October"; then "5 check-ins, 9 proofs". */
function divider(entry: JournalDay, t: T, language: string, today: string) {
  const yesterday = addDays(today, -1);
  const title =
    entry.day === today
      ? t("crew.journal.today")
      : entry.day === yesterday
        ? t("crew.journal.yesterday")
        : formatDayLong(entry.day, language);
  const { check_ins: checkIns, proofs } = entry.summary;
  const parts = [t("crew.journal.checkIns", { count: checkIns })];
  if (proofs > 0) parts.push(t("crew.journal.proofs", { count: proofs }));
  return { title, summary: parts.join(", ") };
}

/**
 * The crew's journal on Echipa: day by day, one card per post, latest first, each as it was
 * posted (a check-in, a "+N", photos added later, a spin drawn or served, the crew's day), each
 * with its own reactions.
 */
export function CrewFeed({
  timeZone,
  members,
  onOpenProofOf,
}: {
  timeZone: string;
  members: Member[];
  /** A member's proof was opened (their new-proofs count resets). */
  onOpenProofOf?: (memberId: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const feed = useJournal();
  const patchReactions = usePatchJournalReactions();
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const pages = feed.data?.pages ?? [];
  const today = todayIn(timeZone);

  const opener = (entry: JournalEntry, caption: string) => (index: number) => {
    if (entry.member) onOpenProofOf?.(entry.member.id);
    setViewing({ items: entry.proofs.map((p) => viewerItem(p, caption)), index });
  };

  function card(entry: JournalEntry) {
    const time = formatWhen(entry.at, language, timeZone);
    const reactions = (
      <Reactions
        target="entry"
        id={entry.id}
        summary={entry.reactions}
        people={members}
        onChange={(summary) => patchReactions(entry.id, summary)}
      />
    );
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
        />
      );
    }
    const { member, challenge } = entry;
    if (!member || !challenge) return null;
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
          onOpenProof={opener(entry, `${who}, ${punishment}`)}
          reactions={reactions}
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
                  entry.day === today ? "crew.journal.todayTotal" : "crew.journal.dayTotal",
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
        onOpenProof={opener(entry, `${who}, ${challenge.title}`)}
        moreLabel={t("feed.more", { count: entry.proofs.length - SHOWN_PROOFS })}
        facts={
          milestone !== undefined && !alone
            ? [`${milestone} ${t("crew.journal.inARow", { count: milestone })}`]
            : facts.streak !== null && facts.streak > 1
              ? [t("crew.journal.streak", { count: facts.streak })]
              : []
        }
        reactions={reactions}
      />
    );
  }

  const days = journal(pages);
  return (
    <section className={styles.section} aria-label={t("crew.journal.label")}>
      {feed.isPending && <Skeleton lines={3} />}
      {feed.isError && <Banner tone="danger" title={errorMessage(t, feed.error)} />}
      {feed.data && days.length === 0 && <p className={styles.muted}>{t("feed.empty")}</p>}
      {days.map((entry) => (
        <Fragment key={entry.day}>
          <DayDivider {...divider(entry, t, language, today)} />
          <Stack gap="sm">
            {entry.cards.map((c) => (
              <Fragment key={c.id}>{card(c)}</Fragment>
            ))}
          </Stack>
        </Fragment>
      ))}
      {feed.hasNextPage && (
        <Button
          variant="ghost"
          loading={feed.isFetchingNextPage}
          onClick={() => void feed.fetchNextPage()}
        >
          {t("feed.older")}
        </Button>
      )}
      <ProofViewer
        items={viewing?.items ?? []}
        index={viewing?.index ?? 0}
        onIndexChange={(index) => setViewing((v) => v && { ...v, index })}
        open={viewing !== null}
        onClose={() => setViewing(null)}
        label={t("proofs.viewer.label")}
        closeLabel={t("common.close")}
        previousLabel={t("proofs.viewer.previous")}
        nextLabel={t("proofs.viewer.next")}
      />
    </section>
  );
}
