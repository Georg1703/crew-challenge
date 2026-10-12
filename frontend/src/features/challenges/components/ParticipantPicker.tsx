import { useTranslation } from "react-i18next";

import { Avatar, CheckList } from "@/shared/ui";

import styles from "../challenges.module.css";

type Person = { id: string; display_name: string; avatar_seed: string };

export type Picked = { participant_ids: string[]; viewer_ids: string[] };

/** Who takes part (the creator always) and, among the others, who only watches. */
export function ParticipantPicker({
  people,
  creatorId,
  values,
  onChange,
  error,
}: {
  people: Person[];
  creatorId: string | undefined;
  values: Picked;
  onChange: (values: Picked) => void;
  error?: string;
}) {
  const { t } = useTranslation();
  const playing = new Set([...values.participant_ids, ...(creatorId ? [creatorId] : [])]);
  const players = people.filter((person) => playing.has(person.id));
  const others = people.filter((person) => !playing.has(person.id));
  const viewers = values.viewer_ids.filter((id) => !playing.has(id));
  const option = (person: Person) => ({
    value: person.id,
    title: person.display_name,
    leading: <Avatar name={person.display_name} seed={person.avatar_seed} size="sm" />,
  });
  return (
    <>
      <CheckList
        label={t("challenges.who.label")}
        values={[...playing]}
        onChange={(ids) =>
          onChange({ participant_ids: ids, viewer_ids: viewers.filter((id) => !ids.includes(id)) })
        }
        error={error}
        options={people.map((person) => ({
          ...option(person),
          description: person.id === creatorId ? t("challenges.who.creator") : undefined,
          disabled: person.id === creatorId,
        }))}
      />
      <p className={styles.meta}>
        {players.length === people.length
          ? t("challenges.who.everyone")
          : t("challenges.who.count", { n: players.length, total: people.length })}
      </p>
      {others.length > 0 && (
        <>
          <CheckList
            label={t("challenges.who.watchLabel")}
            values={viewers}
            onChange={(ids) =>
              onChange({ participant_ids: values.participant_ids, viewer_ids: ids })
            }
            options={others.map(option)}
          />
          <p className={styles.meta}>{t("challenges.who.watchNote")}</p>
        </>
      )}
    </>
  );
}
