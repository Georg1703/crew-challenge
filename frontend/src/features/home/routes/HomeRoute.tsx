import { useTranslation } from "react-i18next";

import { useMe } from "@/features/auth";
import { TodayChallenges } from "@/features/challenges";
import { MemberList, useCrew } from "@/features/crew";
import { InstallCard } from "@/pwa";
import { Screen, Skeleton } from "@/shared/ui";

import styles from "../home.module.css";

/** Today. Until challenges exist it greets the member and shows the crew. */
export function HomeRoute() {
  const { t } = useTranslation();
  const me = useMe();
  const member = me.data?.member;
  const crew = useCrew({ enabled: Boolean(member) });

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
      <TodayChallenges
        isAdmin={member.role === "admin"}
        timeZone={me.data?.crew?.timezone ?? "UTC"}
      />
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>{me.data?.crew?.name ?? t("home.membersTitle")}</h2>
        {crew.data ? (
          <MemberList members={crew.data.members} meId={member.id} />
        ) : (
          <Skeleton lines={3} />
        )}
      </section>
    </Screen>
  );
}
