import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useShallow } from "zustand/react/shallow";

import type { TabAction } from "@/shared/ui";

import { useToday } from "./api";
import { summary, useUploads } from "@/features/proofs";

/**
 * The tab bar's raised check-in button: shown when something runs today, with what is left; while
 * proofs upload, a ring with their progress and how many.
 */
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
  const uploads = useUploads(useShallow((s) => summary(s.items)));
  const action =
    enabled && today.data && today.data.challenges.length > 0
      ? {
          label: uploads.count
            ? t("proofs.uploading", { percent: Math.round(uploads.progress * 100) })
            : t("checkins.tabLabel"),
          icon: "check" as const,
          count: uploads.count || left,
          progress: uploads.count ? uploads.progress : undefined,
          onClick: () => setOpen(true),
        }
      : undefined;
  return { action, open, close: () => setOpen(false) };
}
