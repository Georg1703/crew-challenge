import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router";

import { JournalCard, useJournalCard, useMarkJournalCardRead } from "@/features/checkins";
import { Comments, useThread } from "@/features/comments";
import { errorMessage } from "@/i18n/errors";
import { formatTime } from "@/shared/lib/format";
import { useReducedMotion } from "@/shared/motion";
import {
  Banner,
  Button,
  Icon,
  ProofViewer,
  Quote,
  Screen,
  Skeleton,
  type ViewerItem,
} from "@/shared/ui";

import { useCrew } from "../api";
import styles from "../crew.module.css";

/**
 * A card's own page, full screen, like a Telegram post's comments: a bar with back and the count;
 * the card, then the chat with the message box at the bottom. Once the card scrolls away, the bar
 * pins a line of it (tap: back up to it). `docs/plans/comments.md`.
 */
export function CardRoute() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const still = useReducedMotion();
  const { id = "" } = useParams();
  const crew = useCrew();
  const card = useJournalCard(id);
  const thread = useThread("entry", id);
  const markCardRead = useMarkJournalCardRead();
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const cardBox = useRef<HTMLDivElement>(null);
  const [cardShown, setCardShown] = useState(true);
  const loaded = Boolean(card.data && crew.data);
  useEffect(() => {
    const node = cardBox.current;
    if (!node) return;
    // The bar covers the top of the screen: the card counts as gone once it is under it.
    const watch = new IntersectionObserver(
      ([entry]) => setCardShown(entry?.isIntersecting ?? true),
      { rootMargin: "-72px 0px 0px 0px" },
    );
    watch.observe(node);
    return () => watch.disconnect();
  }, [loaded]);
  // Back where you came from (the feed keeps its place), or to the crew when opened by a link.
  const back = () => (location.key === "default" ? navigate("/crew") : navigate(-1));
  const error = card.error ?? crew.error;
  const entry = card.data;
  const writer = entry?.member;

  return (
    <Screen withTabBar={false}>
      <header className={styles.top}>
        <div className={styles.topRow}>
          <Button
            variant="ghost"
            className={styles.back}
            icon={<Icon name="chevronLeft" size={24} />}
            aria-label={t("comments.back")}
            onClick={back}
          />
          <h1 className={styles.topTitle}>
            {t("comments.title")}
            {thread.data && <span className={styles.count}> {thread.data.length}</span>}
          </h1>
        </div>
        {entry && crew.data && !cardShown && (
          <Quote
            name={writer?.display_name ?? t("crew.journal.crewDayLabel")}
            seed={writer?.avatar_seed ?? crew.data.id}
            text={[
              entry.challenge?.title ?? t("crew.journal.crewDay"),
              formatTime(entry.at, i18n.language, crew.data.timezone),
            ].join(", ")}
            label={t("comments.toCard")}
            onClick={() => window.scrollTo({ top: 0, behavior: still ? "auto" : "smooth" })}
          />
        )}
      </header>
      {(card.isPending || crew.isPending) && !error && <Skeleton lines={5} />}
      {error && <Banner tone="danger" title={errorMessage(t, error)} />}
      {entry && crew.data && (
        <>
          <div ref={cardBox}>
            <JournalCard
              entry={entry}
              members={crew.data.members}
              timeZone={crew.data.timezone}
              onOpenProofs={(items, index) => setViewing({ items, index })}
            />
          </div>
          <Comments
            target="entry"
            id={id}
            people={crew.data.members}
            timeZone={crew.data.timezone}
            onRead={() => markCardRead(id)}
          />
        </>
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
    </Screen>
  );
}
