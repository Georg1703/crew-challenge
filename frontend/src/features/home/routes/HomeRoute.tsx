import { useTranslation } from "react-i18next";

import { useMe } from "@/features/auth";
import { MemberList, useCrew } from "@/features/crew";
import { motion, useSpring, variants } from "@/shared/motion";
import { Card, Screen, Skeleton } from "@/shared/ui";

import styles from "../home.module.css";

/** Placeholder home. The crew garden replaces the member list in a later milestone. */
export function HomeRoute() {
  const { t } = useTranslation();
  const me = useMe();
  const member = me.data?.member;
  const crew = useCrew({ enabled: Boolean(member) });
  const spring = useSpring("gentle");

  if (!member) {
    return (
      <Screen>
        <Card>
          <h1 className={styles.cardTitle}>{t("home.noCrewTitle")}</h1>
          <p className={styles.muted}>{t("home.noCrewBody")}</p>
        </Card>
      </Screen>
    );
  }

  return (
    <Screen>
      <motion.div initial="hidden" animate="visible" variants={variants.fadeUp} transition={spring}>
        <p className={styles.crewName}>{me.data?.crew?.name}</p>
        <h1 className={styles.greeting}>{t("home.greeting", { name: member.display_name })}</h1>
      </motion.div>
      <Card>
        <p className={styles.muted}>{t("home.comingSoon")}</p>
      </Card>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>{t("home.membersTitle")}</h2>
        {crew.data ? (
          <MemberList members={crew.data.members} meId={member.id} />
        ) : (
          <Skeleton lines={3} />
        )}
      </section>
    </Screen>
  );
}
