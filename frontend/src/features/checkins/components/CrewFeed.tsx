import { Fragment, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { CHALLENGE_ICONS } from "@/features/challenges";
import { Reactions } from "@/features/reactions";
import { errorMessage } from "@/i18n/errors";
import { formatDayLong, formatList, formatNumber, formatWhen, todayIn } from "@/shared/lib/format";
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

import { useFeed, usePatchFeedReactions, type FeedItem as Item } from "../api";
import styles from "../checkins.module.css";
import { journal, type JournalCard, type JournalDay } from "../journal";
import { SHOWN_PROOFS, shownTile, viewerItem } from "../proofs";

type T = ReturnType<typeof useTranslation>["t"];

function person(item: Item) {
  return { id: item.member.id, name: item.member.display_name, seed: item.member.avatar_seed };
}

function chip(item: Item) {
  return { icon: CHALLENGE_ICONS[item.challenge.icon], label: item.challenge.title };
}

/** "Today", "Yesterday", else "Monday, 5 October"; then "5 check-ins, 9 proofs". */
function divider(entry: JournalDay, t: T, language: string, today: string) {
  const yesterday = new Date(Date.parse(`${today}T00:00:00Z`) - 86_400_000)
    .toISOString()
    .slice(0, 10);
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

/** The crew's journal on Echipa: day by day, a card per moment, latest first. */
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
  const feed = useFeed();
  const patchReactions = usePatchFeedReactions();
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const items = feed.data?.pages.flatMap((page) => page.results) ?? [];
  const today = todayIn(timeZone);

  /** A check-in's card; `reactable` when it is a card of its own (the server's rule too). */
  function itemCard(item: Item, reactable = false) {
    const who = item.member.display_name;
    const caption = `${who}, ${item.challenge.title}`;
    const unit = item.challenge.unit;
    const quantity = item.challenge.measure === "quantity";
    const milestone = item.milestone?.n;
    const alone = milestone !== undefined && item.proofs.length === 0;
    const total = item.total ?? 0;
    const facts = [t("crew.journal.dayOf", { n: item.day_index, total: item.day_count })];
    if (item.streak !== null && item.streak > 1 && !alone) {
      facts.unshift(t("crew.journal.streak", { count: item.streak }));
    }
    const done = item.week.filter((d) => d.state === "done").length;
    return (
      <FeedCard
        person={person(item)}
        text={
          alone
            ? t("crew.journal.milestone", { name: who })
            : t(
                quantity
                  ? "crew.journal.added"
                  : item.challenge.measure === "abstain"
                    ? "crew.journal.held"
                    : "crew.journal.checked",
                { name: who },
              )
        }
        challenge={chip(item)}
        time={formatWhen(item.activity_at, language, timeZone)}
        tone={alone ? "success" : "default"}
        highlight={
          alone
            ? { value: String(milestone), text: t("crew.journal.inARow", { count: milestone }) }
            : undefined
        }
        amount={
          quantity
            ? {
                value: `+${formatNumber(item.last_amount ?? total, language)} ${unit}`.trim(),
                detail: t(
                  item.day === today ? "crew.journal.todayTotal" : "crew.journal.dayTotal",
                  {
                    total: formatNumber(total, language),
                  },
                ),
                progress:
                  item.target !== null
                    ? {
                        value: total,
                        max: item.target,
                        label: t("crew.journal.ofTarget", {
                          total: formatNumber(total, language),
                          target: formatNumber(item.target, language),
                          unit,
                        }),
                      }
                    : undefined,
              }
            : undefined
        }
        proofs={item.proofs.map((p) => shownTile(p, t, who))}
        onOpenProof={(index) => {
          onOpenProofOf?.(item.member.id);
          setViewing({ items: item.proofs.map((p) => viewerItem(p, caption)), index });
        }}
        moreLabel={t("feed.more", { count: item.proofs.length - SHOWN_PROOFS })}
        week={
          alone
            ? undefined
            : {
                label: t("crew.journal.week", { done }),
                days: item.week.map((d, i) => ({
                  key: d.day,
                  state: d.state,
                  today: i === item.week.length - 1,
                })),
              }
        }
        facts={
          milestone !== undefined && !alone
            ? [`${milestone} ${t("crew.journal.inARow", { count: milestone })}`, ...facts.slice(1)]
            : facts
        }
        reactions={
          reactable ? (
            <Reactions
              target="check_in"
              id={item.id}
              summary={item.reactions}
              people={members}
              onChange={(summary) => patchReactions(item.id, summary)}
            />
          ) : undefined
        }
      />
    );
  }

  function card(entry: JournalCard) {
    if (entry.kind === "item") return itemCard(entry.item, true);
    if (entry.kind === "crew") {
      return (
        <FeedCard
          tone="success"
          people={{
            members: members.map((m) => ({ id: m.id, name: m.display_name, seed: m.avatar_seed })),
            label: t("crew.journal.crewDayLabel"),
          }}
          text={t("crew.journal.crewDay")}
        />
      );
    }
    const [first] = entry.items;
    if (!first) return null;
    if (entry.items.length === 1) return itemCard(first);
    const names = formatList(
      entry.items.map((i) => i.member.display_name),
      language,
    );
    return (
      <FeedCard
        people={{ members: entry.items.map(person), label: names }}
        text={t("crew.journal.group", { names })}
        challenge={chip(first)}
        time={formatWhen(first.activity_at, language, timeZone)}
      />
    );
  }

  return (
    <section className={styles.section} aria-label={t("crew.journal.label")}>
      {feed.isPending && <Skeleton lines={3} />}
      {feed.isError && <Banner tone="danger" title={errorMessage(t, feed.error)} />}
      {feed.data && items.length === 0 && <p className={styles.muted}>{t("feed.empty")}</p>}
      {journal(items).map((entry) => (
        <Fragment key={entry.day}>
          <DayDivider {...divider(entry, t, language, today)} />
          <Stack gap="sm">
            {entry.cards.map((c) => (
              <Fragment key={c.key}>{card(c)}</Fragment>
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
