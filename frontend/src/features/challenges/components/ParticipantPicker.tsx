import { useTranslation } from "react-i18next";

import { Avatar, CheckList } from "@/shared/ui";

import styles from "../challenges.module.css";

type Person = { id: string; display_name: string; avatar_seed: string };

/** Who takes part: the crew as a checklist; the creator is always in. */
export function ParticipantPicker({
  people,
  creatorId,
  values,
  onChange,
  error,
}: {
  people: Person[];
  creatorId: string | undefined;
  values: string[];
  onChange: (values: string[]) => void;
  error?: string;
}) {
  const { t } = useTranslation();
  const chosen = new Set([...values, ...(creatorId ? [creatorId] : [])]);
  const count = people.filter((person) => chosen.has(person.id)).length;
  return (
    <>
      <CheckList
        label={t("challenges.who.label")}
        values={[...chosen]}
        onChange={onChange}
        error={error}
        options={people.map((person) => ({
          value: person.id,
          title: person.display_name,
          description: person.id === creatorId ? t("challenges.who.creator") : undefined,
          leading: <Avatar name={person.display_name} seed={person.avatar_seed} size="sm" />,
          disabled: person.id === creatorId,
        }))}
      />
      <p className={styles.meta}>
        {count === people.length
          ? t("challenges.who.everyone")
          : t("challenges.who.count", { n: count, total: people.length })}
      </p>
    </>
  );
}
