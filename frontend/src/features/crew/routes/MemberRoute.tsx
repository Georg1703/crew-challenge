import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import { CHALLENGE_ICONS } from "@/features/challenges";
import {
  type MemberProgress,
  shownTile,
  SHOWN_PROOFS,
  useMemberProgress,
  useToday,
  viewerItem,
} from "@/features/checkins";
import { errorMessage } from "@/i18n/errors";
import { dayOfMonth } from "@/shared/lib/dates";
import { formatDayLong, monthAndYear, todayIn } from "@/shared/lib/format";
import {
  Banner,
  Card,
  ChallengeChip,
  DayBars,
  DayBarsAxis,
  DayDivider,
  ProofMosaic,
  ProofViewer,
  Screen,
  Skeleton,
  Stack,
  StatGroup,
  StoryAvatar,
  type ViewerItem,
} from "@/shared/ui";

import { useCrew } from "../api";
import styles from "../crew.module.css";
import { markSeen } from "../seen";

const NONE = "-";

type ProofDay = MemberProgress["proof_days"][number];

/** Proof days from the API (latest first, one entry per challenge) grouped under each day. */
function byDay(entries: ProofDay[]): { day: string; entries: ProofDay[] }[] {
  const days: { day: string; entries: ProofDay[] }[] = [];
  for (const entry of entries) {
    const last = days[days.length - 1];
    if (last && last.day === entry.day) last.entries.push(entry);
    else days.push({ day: entry.day, entries: [entry] });
  }
  return days;
}

/** A member's page: their day, their streaks, this month per challenge, and their proofs. */
export function MemberRoute() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const crew = useCrew();
  const today = useToday();
  const progress = useMemberProgress(id);
  const [viewing, setViewing] = useState<{ items: ViewerItem[]; index: number } | null>(null);
  const crewId = crew.data?.id;

  useEffect(() => {
    if (crewId) markSeen(crewId, id);
  }, [crewId, id]);

  if (progress.isPending) {
    return (
      <Screen>
        <Skeleton lines={6} />
      </Screen>
    );
  }
  if (progress.isError) {
    return (
      <Screen title={t("crew.memberPage.title")}>
        <Banner tone="danger" title={errorMessage(t, progress.error)} />
      </Screen>
    );
  }

  const data = progress.data;
  const name = data.member.display_name;
  const row = today.data?.crew.find((r) => r.member.id === id);
  const due = row !== undefined && row.needed > 0;
  const todayDay = todayIn(crew.data?.timezone ?? "UTC");
  const todayIndex = data.days.indexOf(todayDay);
  const share = data.month_due > 0 ? Math.round((data.month_done / data.month_due) * 100) : null;

  return (
    <Screen title={name}>
      <div className={styles.memberHead}>
        <StoryAvatar
          name={name}
          seed={data.member.avatar_seed}
          size="lg"
          segments={row?.challenges.map((c) => c.state) ?? []}
          subtitle={due ? `${row.done}/${row.needed}` : NONE}
          complete={due && row.done >= row.needed}
          label={
            due
              ? t("crew.todayRow", { name, done: row.done, needed: row.needed })
              : t("crew.journal.nothingDue", { name })
          }
        />
      </div>
      <StatGroup
        stats={[
          {
            key: "streak",
            value: String(data.streak),
            label: t("crew.memberPage.streak"),
            tone: data.streak > 0 ? "success" : "default",
          },
          {
            key: "longest",
            value: String(data.longest_streak),
            label: t("crew.memberPage.longest"),
          },
          {
            key: "month",
            value: share === null ? NONE : `${share}%`,
            label: t("crew.memberPage.month", {
              month: monthAndYear(data.days[0] ?? todayDay, language),
            }),
          },
        ]}
      />
      {data.challenges.length === 0 && <p className={styles.muted}>{t("crew.memberPage.none")}</p>}
      {data.challenges.map((c) => (
        <Card key={c.challenge.id}>
          <div className={styles.memberChallenge}>
            <ChallengeChip icon={CHALLENGE_ICONS[c.challenge.icon]} label={c.challenge.title} />
            {c.streak !== null && c.streak > 1 && (
              <span className={styles.muted}>{t("crew.journal.streak", { count: c.streak })}</span>
            )}
          </div>
          <div className={styles.memberBars}>
            <DayBarsAxis
              days={data.days.map(dayOfMonth)}
              todayIndex={todayIndex >= 0 ? todayIndex : undefined}
            />
            <DayBars
              label={t("crew.memberPage.monthOf", { title: c.challenge.title })}
              states={c.states}
              proofs={data.days.map((d) => c.proof_days.includes(d))}
            />
          </div>
        </Card>
      ))}
      <section className={styles.section} aria-label={t("crew.memberPage.proofs")}>
        {data.proof_days.length === 0 && (
          <p className={styles.muted}>{t("crew.memberPage.noProofs")}</p>
        )}
        {byDay(data.proof_days).map(({ day, entries }) => (
          <Fragment key={day}>
            <DayDivider title={formatDayLong(day, language)} />
            <Stack gap="sm">
              {entries.map((entry) => {
                const caption = `${name}, ${entry.challenge.title}`;
                return (
                  <div key={entry.challenge.id} className={styles.memberProofs}>
                    <ChallengeChip
                      icon={CHALLENGE_ICONS[entry.challenge.icon]}
                      label={entry.challenge.title}
                    />
                    <ProofMosaic
                      proofs={entry.proofs.map((p) => shownTile(p, t, name))}
                      onOpen={(index) =>
                        setViewing({
                          items: entry.proofs.map((p) => viewerItem(p, caption)),
                          index,
                        })
                      }
                      moreLabel={t("feed.more", { count: entry.proofs.length - SHOWN_PROOFS })}
                    />
                  </div>
                );
              })}
            </Stack>
          </Fragment>
        ))}
      </section>
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
