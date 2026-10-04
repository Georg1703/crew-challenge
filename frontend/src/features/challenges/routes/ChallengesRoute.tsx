import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useMe } from "@/features/auth";
import { errorMessage } from "@/i18n/errors";
import { monthName } from "@/shared/lib/format";
import { Banner, Button, Icon, Screen, Skeleton } from "@/shared/ui";

import { useChosenChallenges, useCurrentRound } from "../api";
import styles from "../challenges.module.css";
import { ChallengeRows } from "../components/ChallengeRows";
import { RoundProposals } from "../components/RoundProposals";

/** Challenges: next month's proposals and votes, then the active, upcoming and finished ones. */
export function ChallengesRoute() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const me = useMe();
  const round = useCurrentRound();
  const chosen = useChosenChallenges(["active", "upcoming", "finished"]);
  const isAdmin = me.data?.member?.role === "admin";
  const timeZone = me.data?.crew?.timezone ?? "UTC";

  const byPhase = (phase: string) => chosen.data?.filter((c) => c.phase === phase) ?? [];
  const month = round.data ? monthName(round.data.period_start, i18n.language) : "";

  return (
    <Screen title={t("challenges.title")}>
      <Button
        size="lg"
        fullWidth
        icon={<Icon name="plus" size={20} />}
        onClick={() => navigate("/challenges/new")}
      >
        {t("challenges.propose")}
      </Button>

      {(round.isPending || chosen.isPending) && <Skeleton lines={4} />}
      {round.error && <Banner tone="danger" title={errorMessage(t, round.error)} />}

      {round.data && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>{t("challenges.forMonth", { month })}</h2>
          {round.data.proposals.length === 0 ? (
            <p className={styles.muted}>{t("challenges.roundEmpty", { month })}</p>
          ) : (
            <RoundProposals round={round.data} isAdmin={isAdmin} timeZone={timeZone} />
          )}
        </section>
      )}

      {(["active", "upcoming", "finished"] as const).map((phase) =>
        byPhase(phase).length ? (
          <section key={phase} className={styles.section}>
            <h2 className={styles.sectionTitle}>{t(`challenges.sections.${phase}`)}</h2>
            <ChallengeRows challenges={byPhase(phase)} label={t(`challenges.sections.${phase}`)} />
          </section>
        ) : null,
      )}
    </Screen>
  );
}
