import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { formatDay, monthAndYear, monthName, todayIn } from "@/shared/lib/format";
import { Banner, Button, OptionList, Sheet, useToast } from "@/shared/ui";

import { useSchedule, type Challenge } from "../api";
import styles from "../challenges.module.css";
import { monthOptions } from "../months";

/** Admin: pick the month a proposal runs in, or move a scheduled challenge to another month. */
export function ScheduleSheet({
  challenge,
  timeZone,
  open,
  onClose,
}: {
  challenge: Pick<Challenge, "id" | "title" | "state" | "period_start">;
  timeZone: string;
  open: boolean;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const schedule = useSchedule(challenge.id);
  const moving = challenge.state === "chosen";
  const options = monthOptions(todayIn(timeZone)).filter(
    (option) => option.periodStart !== challenge.period_start,
  );
  const [picked, setPicked] = useState<string | null>(null);
  // Default: the first whole month (usually next month).
  const firstWhole = options.find((option) => option.startsOn === option.periodStart);
  const value = picked ?? firstWhole?.periodStart ?? options[0]?.periodStart ?? "";

  const confirm = () =>
    schedule.mutate(value, {
      onSuccess: () => {
        toast(t("challenges.schedule.done", { month: monthName(value, i18n.language) }), "success");
        onClose();
      },
    });

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={
        moving
          ? t("challenges.schedule.moveTitle", { title: challenge.title })
          : t("challenges.schedule.title", { title: challenge.title })
      }
      closeLabel={t("common.close")}
    >
      <OptionList
        label={t("challenges.schedule.month")}
        value={value}
        onChange={setPicked}
        options={options.map((option) => ({
          value: option.periodStart,
          title: monthAndYear(option.periodStart, i18n.language),
          description:
            option.startsOn === option.periodStart
              ? t("challenges.schedule.wholeMonth")
              : t("challenges.schedule.fromTomorrow", {
                  date: formatDay(option.startsOn, i18n.language),
                }),
        }))}
      />
      <p className={styles.muted}>
        {moving ? t("challenges.schedule.moveBody") : t("challenges.schedule.body")}
      </p>
      {schedule.error && <Banner tone="danger" title={errorMessage(t, schedule.error)} />}
      <div className={styles.actions}>
        <Button size="lg" fullWidth loading={schedule.isPending} onClick={confirm}>
          {t("challenges.schedule.confirm", { month: monthName(value, i18n.language) })}
        </Button>
        <Button variant="secondary" size="lg" fullWidth onClick={onClose}>
          {t("common.cancel")}
        </Button>
      </div>
    </Sheet>
  );
}
