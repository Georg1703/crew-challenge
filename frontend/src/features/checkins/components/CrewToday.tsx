import { useTranslation } from "react-i18next";

import { Avatar } from "@/shared/ui";

import type { Today } from "../api";
import styles from "../checkins.module.css";

/** Everyone's day at a glance: the today ring on each avatar and "2/3". */
export function CrewToday({ crew, meId }: { crew: Today["crew"]; meId?: string }) {
  const { t } = useTranslation();
  if (crew.length === 0) return null;
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{t("checkins.crewTitle")}</h2>
      <ul className={styles.crew}>
        {crew.map((row) => {
          const done = row.needed > 0 && row.done >= row.needed;
          const name = row.member.id === meId ? t("crew.you") : row.member.display_name;
          return (
            <li key={row.member.id} className={styles.person}>
              <Avatar
                name={row.member.display_name}
                seed={row.member.avatar_seed}
                size="lg"
                ring={done ? "done" : "todo"}
                label={t("checkins.crewRow", {
                  name: row.member.display_name,
                  done: row.done,
                  needed: row.needed,
                })}
              />
              <span className={styles.personName}>{name}</span>
              <span className={styles.meta}>
                {t("checkins.fraction", { done: row.done, total: row.needed })}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
