import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { formatNumber, formatWhen } from "@/shared/lib/format";
import {
  Banner,
  Button,
  FeedCard,
  ProofViewer,
  Skeleton,
  Stack,
  type ViewerItem,
} from "@/shared/ui";

import { useFeed, type FeedItem as Item } from "../api";
import styles from "../checkins.module.css";
import { SHOWN_PROOFS, shownTile, viewerItem } from "../proofs";

/** "Ana checked in Walk", "Ana held on: No sugar", "Ana: 20 pages · Read". */
function says(item: Item, t: ReturnType<typeof useTranslation>["t"], language: string): string {
  const name = item.member.display_name;
  const title = item.challenge.title;
  if (item.total !== null) {
    return t("feed.amount", {
      name,
      title,
      total: formatNumber(item.total, language),
      unit: item.challenge.unit,
    });
  }
  return t(item.challenge.measure === "abstain" ? "feed.held" : "feed.checked", { name, title });
}

/** Activity on Echipa: the crew's check-ins and their proofs, latest first, older on request. */
export function CrewFeed({ timeZone }: { timeZone: string }) {
  const { t, i18n } = useTranslation();
  const feed = useFeed();
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const items = feed.data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <section className={styles.section} aria-label={t("feed.title")}>
      <h2 className={styles.sectionTitle}>{t("feed.title")}</h2>
      {feed.isPending && <Skeleton lines={3} />}
      {feed.isError && <Banner tone="danger" title={errorMessage(t, feed.error)} />}
      {feed.data && items.length === 0 && <p className={styles.muted}>{t("feed.empty")}</p>}
      {items.length > 0 && (
        <Stack gap="sm">
          {items.map((item) => {
            const who = item.member.display_name;
            const caption = `${who}, ${item.challenge.title}`;
            return (
              <FeedCard
                key={item.id}
                person={{ id: item.member.id, name: who, seed: item.member.avatar_seed }}
                text={says(item, t, i18n.language)}
                time={formatWhen(item.activity_at, i18n.language, timeZone)}
                proofs={item.proofs.map((p) => shownTile(p, t, who))}
                onOpenProof={(index) =>
                  setViewing({ items: item.proofs.map((p) => viewerItem(p, caption)), index })
                }
                moreLabel={t("feed.more", { count: item.proofs.length - SHOWN_PROOFS })}
              />
            );
          })}
        </Stack>
      )}
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
