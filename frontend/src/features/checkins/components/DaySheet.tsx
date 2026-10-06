import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { formatDayLong, formatNumber } from "@/shared/lib/format";
import {
  Banner,
  Button,
  FeedItem,
  Icon,
  List,
  ProofViewer,
  Sheet,
  Skeleton,
  type ViewerItem,
} from "@/shared/ui";

import { useDaySheet } from "../api";
import styles from "../checkins.module.css";
import { SHOWN_PROOFS, shownTile, viewerItem } from "../proofs";

/**
 * One day of a challenge, opened from its board: everyone's state, total and proofs. The arrows
 * move to the day before or after (within `days`), so a tap that missed by one is one more tap.
 */
export function DaySheet({
  challengeId,
  title,
  unit,
  days,
  day,
  open,
  onDay,
  onClose,
}: {
  challengeId: string;
  title: string;
  unit: string;
  days: string[];
  day: string;
  open: boolean;
  onDay: (day: string) => void;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const sheet = useDaySheet(challengeId, day);
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const at = days.indexOf(day);
  const before = days[at - 1];
  const after = days[at + 1];

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={formatDayLong(day, i18n.language)}
      closeLabel={t("common.close")}
    >
      <div className={styles.dayNav}>
        <Button
          variant="ghost"
          aria-label={t("checkins.day.previous")}
          disabled={!before}
          icon={<Icon name="chevronLeft" size={20} />}
          onClick={() => before && onDay(before)}
        />
        <span className={styles.meta}>{title}</span>
        <Button
          variant="ghost"
          aria-label={t("checkins.day.next")}
          disabled={!after}
          icon={<Icon name="chevronRight" size={20} />}
          onClick={() => after && onDay(after)}
        />
      </div>
      {sheet.isPending && <Skeleton lines={3} />}
      {sheet.error && <Banner tone="danger" title={errorMessage(t, sheet.error)} />}
      {sheet.data && (
        <List label={formatDayLong(day, i18n.language)}>
          {sheet.data.map((row) => {
            const who = row.member.display_name;
            const state = t(`checkins.states.${row.state}`);
            return (
              <FeedItem
                key={row.member.id}
                name={who}
                seed={row.member.avatar_seed}
                text={who}
                time={
                  row.total === null
                    ? state
                    : `${state} · ${formatNumber(row.total, i18n.language)} ${unit}`.trim()
                }
                proofs={row.proofs.map((p) => shownTile(p, t, who))}
                onOpenProof={(index) =>
                  setViewing({
                    items: row.proofs.map((p) => viewerItem(p, `${who}, ${title}`)),
                    index,
                  })
                }
                moreLabel={t("feed.more", { count: row.proofs.length - SHOWN_PROOFS })}
              />
            );
          })}
        </List>
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
    </Sheet>
  );
}
