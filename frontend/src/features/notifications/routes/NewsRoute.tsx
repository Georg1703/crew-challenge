import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useCrew } from "@/features/crew";
import { errorMessage } from "@/i18n/errors";
import { formatWhen } from "@/shared/lib/format";
import {
  Avatar,
  Banner,
  Button,
  Icon,
  List,
  ListRow,
  Screen,
  Skeleton,
  StatusPill,
} from "@/shared/ui";

import { useMarkNewsRead, useNews, type Notification } from "../api";
import styles from "../notifications.module.css";

/** Where a tap on a line goes: the page that shows what happened. */
export function newsLink(item: Notification): string {
  return item.target.type === "entry" ? `/crew/cards/${item.target.id}` : "/crew";
}

/**
 * News: who reacted to, commented on or answered what is yours, latest first. Opening the page
 * marks it all read (the badge clears); a line keeps its mark until the next refresh.
 */
// What each kind says after the actor's name; reactions say their emoji instead.
const LINES: Partial<Record<Notification["kind"], string>> = {
  comment: "news.comment",
  reply: "news.reply",
  mention: "news.mention",
};

export function NewsRoute() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const crew = useCrew();
  const news = useNews();
  const markRead = useMarkNewsRead();
  const unread = news.data?.unread ?? 0;
  const mark = markRead.mutate;
  useEffect(() => {
    if (unread > 0) mark();
  }, [unread, mark]);

  const line = (item: Notification) => {
    const { kind, facts } = item;
    if (kind === "reaction") {
      const key = facts.on === "comment" ? "news.reactionComment" : "news.reactionEntry";
      return t(key, { emoji: facts.emoji ?? "" });
    }
    return t(LINES[kind] ?? "news.comment");
  };

  return (
    <Screen
      title={t("news.title")}
      action={
        <Button
          variant="ghost"
          aria-label={t("comments.back")}
          icon={<Icon name="chevronLeft" size={22} />}
          onClick={() => navigate("/crew")}
        />
      }
    >
      {news.isPending && <Skeleton lines={4} />}
      {news.isError && <Banner tone="danger" title={errorMessage(t, news.error)} />}
      {news.data && news.data.results.length === 0 && (
        <p className={styles.muted}>{t("news.empty")}</p>
      )}
      {news.data && news.data.results.length > 0 && (
        <List label={t("news.title")}>
          {news.data.results.map((item) => {
            const when = formatWhen(item.created_at, i18n.language, crew.data?.timezone ?? "UTC");
            const text = item.facts.text;
            return (
              <ListRow
                key={item.id}
                to={newsLink(item)}
                leading={
                  <Avatar name={item.actor.display_name} seed={item.actor.avatar_seed} size="sm" />
                }
                title={
                  <>
                    <strong>{item.actor.display_name}</strong> {line(item)}
                  </>
                }
                subtitle={text ? `${text} - ${when}` : when}
                trailing={
                  item.read_at ? undefined : <StatusPill tone="accent">{t("news.new")}</StatusPill>
                }
              />
            );
          })}
        </List>
      )}
    </Screen>
  );
}
