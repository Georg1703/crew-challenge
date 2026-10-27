import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button, Card, Icon } from "@/shared/ui";

import styles from "../notifications.module.css";
import { checkedInOnce, dismissPrompt, promptDismissed, pushPermission } from "../push";
import { usePush } from "../usePush";

/**
 * Today: "want to know when the crew reacts?", once a check-in has been posted on this device
 * and never on first load. "Not now" hides it for two weeks; on, blocked or unavailable: gone.
 */
export function PushPrompt() {
  const { t } = useTranslation();
  const push = usePush();
  const [hidden, setHidden] = useState(() => !checkedInOnce() || promptDismissed());
  if (hidden || push.state !== "off" || pushPermission() !== "default") return null;
  const dismiss = () => {
    dismissPrompt();
    setHidden(true);
  };
  return (
    <Card>
      <div className={styles.prompt}>
        <span className={styles.promptIcon}>
          <Icon name="bell" />
        </span>
        <div>
          <h2 className={styles.cardTitle}>{t("push.promptTitle")}</h2>
          <p className={styles.muted}>{t("push.promptBody")}</p>
        </div>
      </div>
      <div className={styles.promptActions}>
        <Button variant="ghost" onClick={dismiss}>
          {t("push.notNow")}
        </Button>
        <Button loading={push.busy} onClick={() => void push.enable()}>
          {t("push.turnOn")}
        </Button>
      </div>
    </Card>
  );
}
