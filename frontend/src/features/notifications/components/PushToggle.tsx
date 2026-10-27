import { useTranslation } from "react-i18next";

import { Card, Toggle } from "@/shared/ui";

import styles from "../notifications.module.css";
import { usePush } from "../usePush";

/** Me: push notifications on this device, on or off; what stands in the way when they cannot. */
export function PushToggle() {
  const { t } = useTranslation();
  const push = usePush();
  if (push.state === "unavailable" || push.state === "unknown") return null;
  if (push.state === "install") {
    return (
      <Card>
        <h2 className={styles.cardTitle}>{t("push.title")}</h2>
        <p className={styles.muted}>{t("push.install")}</p>
      </Card>
    );
  }
  const description =
    push.state === "denied"
      ? t("push.denied")
      : push.failed
        ? t("push.failed")
        : t("push.toggleHint");
  return (
    <Card>
      <Toggle
        label={t("push.toggle")}
        description={description}
        checked={push.state === "on"}
        onChange={(on) => {
          if (push.busy || push.state === "denied") return;
          void (on ? push.enable() : push.disable());
        }}
      />
    </Card>
  );
}
