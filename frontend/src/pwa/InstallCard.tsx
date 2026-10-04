import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button, Card, Icon } from "@/shared/ui";

import { useInstallPrompt } from "./installPrompt";
import { IosInstallGuide } from "./IosInstallGuide";
import { detectPlatform } from "./platform";
import styles from "./pwa.module.css";

const DISMISS_KEY = "install-card-dismissed-at";
const DISMISS_FOR_MS = 14 * 24 * 60 * 60 * 1000;

function dismissedRecently(): boolean {
  try {
    const at = Number(localStorage.getItem(DISMISS_KEY));
    return Boolean(at) && Date.now() - at < DISMISS_FOR_MS;
  } catch {
    return false;
  }
}

/**
 * Invites the user to install the app: Android/desktop get the browser's dialog, iOS gets the
 * step-by-step guide. Hidden when already installed or when the browser cannot install.
 * With `dismissible`, "Not now" hides it for two weeks on this device.
 */
export function InstallCard({ dismissible = false }: { dismissible?: boolean }) {
  const { t } = useTranslation();
  const { canPrompt, justInstalled, prompt } = useInstallPrompt();
  const [platform] = useState(detectPlatform);
  const [guideOpen, setGuideOpen] = useState(false);
  const [hidden, setHidden] = useState(() => dismissible && dismissedRecently());

  const available = platform.ios || canPrompt;
  if (platform.standalone || justInstalled || hidden || !available) return null;

  const dismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      // Not critical.
    }
    setHidden(true);
  };

  return (
    <Card>
      <div className={styles.install}>
        <span className={styles.installIcon}>
          <Icon name="download" />
        </span>
        <div>
          <h2 className={styles.installTitle}>{t("pwa.installTitle")}</h2>
          <p className={styles.muted}>{t("pwa.installBody")}</p>
        </div>
      </div>
      <div className={styles.actions}>
        {dismissible && (
          <Button variant="ghost" onClick={dismiss}>
            {t("pwa.notNow")}
          </Button>
        )}
        <Button onClick={() => (platform.ios ? setGuideOpen(true) : void prompt())}>
          {t("pwa.install")}
        </Button>
      </div>
      {platform.ios && <IosInstallGuide open={guideOpen} onClose={() => setGuideOpen(false)} />}
    </Card>
  );
}
