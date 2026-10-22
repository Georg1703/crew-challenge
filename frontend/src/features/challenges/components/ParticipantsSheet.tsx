import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useMe } from "@/features/auth";
import { useCrew } from "@/features/crew";
import { errorMessage } from "@/i18n/errors";
import { Banner, Button, Sheet, Skeleton, useToast } from "@/shared/ui";

import { useSetParticipants, type Challenge } from "../api";
import styles from "../challenges.module.css";
import { ParticipantPicker, pickedFrom } from "./ParticipantPicker";

/** The creator changes who takes part and who watches while the challenge is a proposal. Once
 * scheduled, the creator or an admin only adds people: nobody in it is taken out. */
export function ParticipantsSheet({
  challenge,
  onClose,
}: {
  challenge: Pick<Challenge, "id" | "participants" | "state" | "phase">;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const me = useMe();
  const crew = useCrew();
  const save = useSetParticipants(challenge.id);
  const [values, setValues] = useState(() => pickedFrom(challenge.participants));
  const adding = challenge.state === "chosen";
  const left = new Set(challenge.participants.filter((p) => p.left_on).map((p) => p.member.id));
  const note = !adding
    ? "challenges.who.note"
    : challenge.phase === "upcoming"
      ? "challenges.who.addNoteBefore"
      : "challenges.who.addNote";

  const confirm = () =>
    save.mutate(values, {
      onSuccess: () => {
        toast(t("challenges.who.saved"), "success");
        onClose();
      },
    });

  return (
    <Sheet
      open
      onClose={onClose}
      title={t(adding ? "challenges.who.add" : "challenges.who.edit")}
      closeLabel={t("common.close")}
    >
      {crew.data ? (
        <ParticipantPicker
          people={crew.data.members.filter((person) => !left.has(person.id))}
          creatorId={adding ? undefined : me.data?.member?.id}
          locked={adding ? pickedFrom(challenge.participants) : undefined}
          crewSize={crew.data.members.length}
          values={values}
          onChange={setValues}
        />
      ) : (
        <Skeleton lines={4} />
      )}
      <p className={styles.muted}>{t(note)}</p>
      {save.error && <Banner tone="danger" title={errorMessage(t, save.error)} />}
      <div className={styles.actions}>
        <Button size="lg" fullWidth loading={save.isPending} onClick={confirm}>
          {t("challenges.who.save")}
        </Button>
        <Button variant="secondary" size="lg" fullWidth onClick={onClose}>
          {t("common.cancel")}
        </Button>
      </div>
    </Sheet>
  );
}
