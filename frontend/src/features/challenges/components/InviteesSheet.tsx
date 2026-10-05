import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useMe } from "@/features/auth";
import { useCrew } from "@/features/crew";
import { errorMessage } from "@/i18n/errors";
import { Banner, Button, Sheet, Skeleton, useToast } from "@/shared/ui";

import { useSetInvitees, type Challenge } from "../api";
import styles from "../challenges.module.css";
import { InviteePicker } from "./InviteePicker";

/** The creator changes who takes part while the challenge is a proposal. */
export function InviteesSheet({
  challenge,
  onClose,
}: {
  challenge: Pick<Challenge, "id" | "invitees">;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const me = useMe();
  const crew = useCrew();
  const save = useSetInvitees(challenge.id);
  const [values, setValues] = useState(challenge.invitees.map((person) => person.id));

  const confirm = () =>
    save.mutate(values, {
      onSuccess: () => {
        toast(t("challenges.who.saved"), "success");
        onClose();
      },
    });

  return (
    <Sheet open onClose={onClose} title={t("challenges.who.edit")} closeLabel={t("common.close")}>
      {crew.data ? (
        <InviteePicker
          people={crew.data.members}
          creatorId={me.data?.member?.id}
          values={values}
          onChange={setValues}
        />
      ) : (
        <Skeleton lines={4} />
      )}
      <p className={styles.muted}>{t("challenges.who.note")}</p>
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
