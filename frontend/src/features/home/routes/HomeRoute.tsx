import { useTranslation } from "react-i18next";

import { useMe } from "@/features/auth";
import { ActiveChallenges } from "@/features/challenges";
import { InstallCard } from "@/pwa";
import { Screen } from "@/shared/ui";

import styles from "../home.module.css";

/** Today: the challenges running now. Proposals, votes and the crew are in the Crew tab. */
export function HomeRoute() {
  const { t } = useTranslation();
  const me = useMe();
  const member = me.data?.member;

  if (!member) {
    return (
      <Screen title={t("home.noCrewTitle")}>
        <p className={styles.muted}>{t("home.noCrewBody")}</p>
      </Screen>
    );
  }

  return (
    <Screen title={t("home.greeting", { name: member.display_name })}>
      <InstallCard dismissible />
      <ActiveChallenges />
    </Screen>
  );
}
