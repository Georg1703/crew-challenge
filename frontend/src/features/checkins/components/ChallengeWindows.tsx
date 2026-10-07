import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { formatNumber } from "@/shared/lib/format";
import { Banner, List, ListRow, Skeleton, StatusPill } from "@/shared/ui";

import { useWindows, type Window } from "../api";
import styles from "../checkins.module.css";
import { windowAmount, windowDays, windowKind, type WindowRule } from "../windows";

const TONES = { met: "success", failed: "danger", open: "accent", future: "neutral" } as const;

/**
 * A scheduled challenge's weeks, months or whole period: what each asks for (less when cut short)
 * and, for a participant, how far they got and how it stands.
 */
export function ChallengeWindows({ challengeId, rule }: { challengeId: string; rule: WindowRule }) {
  const { t, i18n } = useTranslation();
  const windows = useWindows(challengeId);
  const title = t(`windows.title.${windowKind(rule)}`);
  const amount = (value: number) => windowAmount(t, value, rule, i18n.language);

  const line = (w: Window) => {
    const text =
      w.done === null
        ? t("windows.asks", { need: amount(w.need) })
        : t("windows.done", { done: formatNumber(w.done, i18n.language), need: amount(w.need) });
    return w.need < w.full_need ? t("windows.cut", { text, full: amount(w.full_need) }) : text;
  };

  if (windows.data?.length === 0) return null;
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {windows.isPending ? (
        <Skeleton lines={3} />
      ) : windows.error ? (
        <Banner tone="danger" title={errorMessage(t, windows.error)} />
      ) : (
        <List label={title}>
          {windows.data.map((w) => (
            <ListRow
              key={w.first}
              title={windowDays(t, w, i18n.language)}
              subtitle={line(w)}
              trailing={
                w.state && (
                  <StatusPill tone={TONES[w.state]}>{t(`windows.states.${w.state}`)}</StatusPill>
                )
              }
            />
          ))}
        </List>
      )}
    </section>
  );
}
