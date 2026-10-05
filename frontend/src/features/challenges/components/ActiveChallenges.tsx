import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { errorMessage } from "@/i18n/errors";
import { formatDay } from "@/shared/lib/format";
import { Banner, Button, Card, Skeleton } from "@/shared/ui";

import { useChosenChallenges } from "../api";
import styles from "../challenges.module.css";
import { summaryLine } from "../describe";

/** Today: only the challenges running now. Proposals and votes live in the Crew tab. */
export function ActiveChallenges() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const active = useChosenChallenges(["active"]);

  if (active.isPending) return <Skeleton lines={3} />;
  if (active.error) return <Banner tone="danger" title={errorMessage(t, active.error)} />;

  if (active.data.length === 0) {
    return (
      <Card>
        <h2 className={styles.cardTitle}>{t("home.noChallengeTitle")}</h2>
        <p className={styles.muted}>{t("home.noChallengeBody")}</p>
      </Card>
    );
  }

  return (
    <>
      {active.data.map((challenge) => (
        <Card key={challenge.id}>
          <h2 className={styles.cardTitle}>{challenge.title}</h2>
          <p className={styles.meta}>{summaryLine(t, challenge, i18n.language)}</p>
          {challenge.end_date && (
            <p className={styles.meta}>
              {t("challenges.until", { date: formatDay(challenge.end_date, i18n.language) })}
            </p>
          )}
          <Button variant="secondary" onClick={() => navigate(`/challenges/${challenge.id}`)}>
            {t("challenges.open")}
          </Button>
        </Card>
      ))}
    </>
  );
}
