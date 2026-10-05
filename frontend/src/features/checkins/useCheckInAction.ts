import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { TabAction } from "@/shared/ui";

import { useToday } from "./api";

/** The tab bar's raised check-in button: shown when something runs today, with what is left. */
export function useCheckInAction(enabled: boolean): {
  action: TabAction | undefined;
  open: boolean;
  close: () => void;
} {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const today = useToday({ enabled });
  const segments = today.data?.challenges.filter((c) => c.settled !== null) ?? [];
  const left = segments.filter((c) => !c.settled).length;
  const action =
    enabled && today.data && today.data.challenges.length > 0
      ? {
          label: t("checkins.tabLabel"),
          icon: "check" as const,
          count: left,
          onClick: () => setOpen(true),
        }
      : undefined;
  return { action, open, close: () => setOpen(false) };
}
