import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { formatDay, monthName } from "@/shared/lib/format";
import { Banner, Button, Sheet, useToast } from "@/shared/ui";

import { useChoose, type Proposal, type Round } from "../api";
import styles from "../challenges.module.css";

/** Admin: confirm which proposal becomes the period's challenge. */
export function ChooseSheet({
  round,
  proposal,
  onClose,
}: {
  round: Round;
  proposal: Proposal | null;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const choose = useChoose();
  const month = monthName(round.period_start, i18n.language);

  const confirm = () => {
    if (!proposal) return;
    choose.mutate(
      { roundId: round.id, challengeId: proposal.id },
      {
        onSuccess: () => {
          toast(t("challenges.chosenToast", { month }), "success");
          onClose();
        },
      },
    );
  };

  return (
    <Sheet
      open={proposal !== null}
      onClose={onClose}
      title={t("challenges.chooseTitle", { title: proposal?.title ?? "", month })}
      closeLabel={t("common.close")}
    >
      <p className={styles.muted}>
        {t("challenges.chooseBody", { date: formatDay(round.period_start, i18n.language) })}
      </p>
      {choose.error && <Banner tone="danger" title={errorMessage(t, choose.error)} />}
      <div className={styles.actions}>
        <Button size="lg" fullWidth loading={choose.isPending} onClick={confirm}>
          {t("challenges.chooseConfirm")}
        </Button>
        <Button variant="secondary" size="lg" fullWidth onClick={onClose}>
          {t("common.cancel")}
        </Button>
      </div>
    </Sheet>
  );
}
