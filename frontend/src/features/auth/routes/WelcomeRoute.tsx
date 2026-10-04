import { useTranslation } from "react-i18next";
import { Navigate, useNavigate } from "react-router";

import { useInstallStep } from "@/pwa";
import { Button, Icon, IconTile, Screen, Skeleton, type IconName } from "@/shared/ui";

import { useMe } from "../api";
import styles from "../auth.module.css";

const STEPS: { icon: IconName; title: string; body: string }[] = [
  { icon: "camera", title: "welcome.checkInTitle", body: "welcome.checkInBody" },
  { icon: "users", title: "welcome.crewTitle", body: "welcome.crewBody" },
  { icon: "clock", title: "welcome.dayTitle", body: "welcome.dayBody" },
];

/** 1.4 Welcome to the crew, right after joining. "Start" offers to install, then opens Today. */
export function WelcomeRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const me = useMe();
  const install = useInstallStep();
  const member = me.data?.member;
  const crew = me.data?.crew;

  if (me.isPending) {
    return (
      <Screen withTabBar={false}>
        <Skeleton lines={4} />
      </Screen>
    );
  }
  if (!member || !crew) return <Navigate to="/" replace />;

  return (
    <Screen withTabBar={false} title={t("welcome.title", { name: member.display_name })}>
      <p className={styles.muted}>{t("welcome.body", { crew: crew.name })}</p>
      <ul className={styles.steps}>
        {STEPS.map((step) => (
          <li key={step.icon} className={styles.step}>
            <IconTile tone="accent">
              <Icon name={step.icon} size={20} />
            </IconTile>
            <span className={styles.stepText}>
              <span className={styles.stepTitle}>{t(step.title)}</span>
              <span className={styles.stepBody}>{t(step.body, { timezone: crew.timezone })}</span>
            </span>
          </li>
        ))}
      </ul>
      <Button
        size="lg"
        fullWidth
        onClick={() => install.begin(() => navigate("/", { replace: true }))}
      >
        {t("welcome.start")}
      </Button>
      {install.guide}
    </Screen>
  );
}
