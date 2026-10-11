import { Fragment, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { errorMessage } from "@/i18n/errors";
import { addDays } from "@/shared/lib/dates";
import { formatDayLong, todayIn } from "@/shared/lib/format";
import {
  Banner,
  Button,
  DayDivider,
  ProofViewer,
  Skeleton,
  Stack,
  type ViewerItem,
} from "@/shared/ui";

import { useJournal } from "../api";
import styles from "../checkins.module.css";
import { journal, type JournalDay } from "../journal";
import { JournalCard } from "./JournalCard";

type T = ReturnType<typeof useTranslation>["t"];

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
 * with its own reactions and the link to its comments.
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
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const pages = feed.data?.pages ?? [];
  const today = todayIn(timeZone);

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
            {entry.cards.map((card) => (
              <JournalCard
                key={card.id}
                entry={card}
                members={members}
                timeZone={timeZone}
                onOpenProofs={(items, index) => {
                  if (card.member) onOpenProofOf?.(card.member.id);
                  setViewing({ items, index });
                }}
                withComments
              />
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
