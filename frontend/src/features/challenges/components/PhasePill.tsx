import { useTranslation } from "react-i18next";

import { StatusPill } from "@/shared/ui";

import type { Challenge } from "../api";

/** Where a challenge stands: proposal, not chosen, upcoming, active, finished. */
export function PhasePill({ challenge }: { challenge: Challenge }) {
  const { t } = useTranslation();
  if (challenge.state === "proposed")
    return <StatusPill>{t("challenges.state.proposed")}</StatusPill>;
  if (challenge.state === "not_chosen")
    return <StatusPill>{t("challenges.state.notChosen")}</StatusPill>;
  if (challenge.phase === "active")
    return <StatusPill tone="success">{t("challenges.phase.active")}</StatusPill>;
  if (challenge.phase === "upcoming")
    return <StatusPill tone="accent">{t("challenges.phase.upcoming")}</StatusPill>;
  return <StatusPill>{t("challenges.phase.finished")}</StatusPill>;
}
