import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useMe } from "@/features/auth";
import { errorMessage } from "@/i18n/errors";
import { monthAndYear } from "@/shared/lib/format";
import { Banner, Button, Icon, Screen, Segmented, Skeleton } from "@/shared/ui";

import { useChosenChallenges, usePool, type Challenge } from "../api";
import styles from "../challenges.module.css";
import { ChallengeRows } from "../components/ChallengeRows";
import { PoolProposals } from "../components/PoolProposals";

type Sort = "newest" | "votes";

/** Groups scheduled challenges by the month they belong to, in order. */
function byMonth(challenges: Challenge[]): [string, Challenge[]][] {
  const groups = new Map<string, Challenge[]>();
  for (const challenge of challenges) {
    const key = challenge.period_start ?? "";
    groups.set(key, [...(groups.get(key) ?? []), challenge]);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

/** Challenges: running and coming up, the crew's pool of proposals, then the finished ones. */
export function ChallengesRoute() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const me = useMe();
  const pool = usePool();
  const chosen = useChosenChallenges(["active", "upcoming", "finished"]);
  const [sort, setSort] = useState<Sort>("newest");
  const isAdmin = me.data?.member?.role === "admin";
  const timeZone = me.data?.crew?.timezone ?? "UTC";

  const inPhase = (phase: string) => chosen.data?.filter((c) => c.phase === phase) ?? [];
  const full = pool.data ? pool.data.size >= pool.data.limit : false;
  const proposals = [...(pool.data?.proposals ?? [])];
  if (sort === "votes") proposals.sort((a, b) => b.vote_count - a.vote_count);

  return (
    <Screen title={t("challenges.title")}>
      <Button
        size="lg"
        fullWidth
        icon={<Icon name="plus" size={20} />}
        disabled={full}
        onClick={() => navigate("/challenges/new")}
      >
        {t("challenges.propose")}
      </Button>
      {full && pool.data && (
        <p className={styles.meta}>{t("challenges.poolFull", { limit: pool.data.limit })}</p>
      )}

      {(pool.isPending || chosen.isPending) && <Skeleton lines={4} />}
      {pool.error && <Banner tone="danger" title={errorMessage(t, pool.error)} />}
      {chosen.error && <Banner tone="danger" title={errorMessage(t, chosen.error)} />}

      {inPhase("active").length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t("challenges.sections.active")}</h2>
          <ChallengeRows challenges={inPhase("active")} label={t("challenges.sections.active")} />
        </section>
      )}

      {inPhase("upcoming").length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t("challenges.sections.upcoming")}</h2>
          {byMonth(inPhase("upcoming")).map(([month, challenges]) => {
            const label = month ? monthAndYear(month, i18n.language) : "";
            return (
              <div key={month} className={styles.group}>
                <h3 className={styles.groupTitle}>{label}</h3>
                <ChallengeRows challenges={challenges} label={label} />
              </div>
            );
          })}
        </section>
      )}

      {pool.data && (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>{t("challenges.sections.pool")}</h2>
            <span className={styles.meta}>
              {t("challenges.poolSize", { n: pool.data.size, limit: pool.data.limit })}
            </span>
          </div>
          {pool.data.proposals.length === 0 ? (
            <p className={styles.muted}>{t("challenges.poolEmpty")}</p>
          ) : (
            <>
              {isAdmin && pool.data.proposals.length > 1 && (
                <Segmented<Sort>
                  label={t("challenges.sort.label")}
                  value={sort}
                  onChange={setSort}
                  options={[
                    { value: "newest", label: t("challenges.sort.newest") },
                    { value: "votes", label: t("challenges.sort.votes") },
                  ]}
                />
              )}
              <PoolProposals proposals={proposals} isAdmin={isAdmin} timeZone={timeZone} />
            </>
          )}
        </section>
      )}

      {inPhase("finished").length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t("challenges.sections.finished")}</h2>
          <ChallengeRows
            challenges={inPhase("finished")}
            label={t("challenges.sections.finished")}
          />
        </section>
      )}
    </Screen>
  );
}
