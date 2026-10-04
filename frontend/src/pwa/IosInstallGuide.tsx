import { useTranslation } from "react-i18next";

import { motion, staggerStep, useSpring, variants } from "@/shared/motion";
import { Button, Icon, Sheet, type IconName } from "@/shared/ui";

import styles from "./pwa.module.css";

const STEPS: { key: "iosStep1" | "iosStep2" | "iosStep3"; icon: IconName }[] = [
  { key: "iosStep1", icon: "share" },
  { key: "iosStep2", icon: "addSquare" },
  { key: "iosStep3", icon: "check" },
];

/** iOS has no install prompt: show the three taps, with the Share button pointing down. */
export function IosInstallGuide({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const spring = useSpring("bouncy");
  return (
    <Sheet open={open} onClose={onClose} title={t("pwa.iosTitle")} closeLabel={t("common.close")}>
      <motion.ol
        className={styles.steps}
        initial="hidden"
        animate="visible"
        transition={{ staggerChildren: staggerStep * 3 }}
      >
        {STEPS.map((step, index) => (
          <motion.li
            key={step.key}
            className={styles.step}
            variants={variants.popIn}
            transition={spring}
          >
            <span className={styles.stepIcon}>
              <Icon name={step.icon} />
            </span>
            <span className={styles.stepNumber}>{index + 1}</span>
            <span>{t(`pwa.${step.key}`)}</span>
          </motion.li>
        ))}
      </motion.ol>
      <p className={styles.hint}>
        <span className={styles.pointer} aria-hidden="true">
          <Icon name="download" />
        </span>
        {t("pwa.iosHint")}
      </p>
      <Button fullWidth onClick={onClose}>
        {t("pwa.iosDone")}
      </Button>
    </Sheet>
  );
}
