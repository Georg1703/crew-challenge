import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "@/i18n/errors";
import { addDays, periodEnd } from "@/shared/lib/dates";
import { formatDay, monthAndYear, monthName, todayIn } from "@/shared/lib/format";
import { Banner, Button, OptionList, Sheet, TextField, useToast } from "@/shared/ui";

import { useSchedule, type Challenge } from "../api";
import styles from "../challenges.module.css";
import { startOptions } from "../periods";

/**
 * Admin: pick when a proposal starts, or move a scheduled challenge before it starts. How long it
 * runs came with the proposal: a month (the 1st), a week (a Monday) or any day from tomorrow.
 */
export function ScheduleSheet({
  challenge,
  timeZone,
  open,
  onClose,
}: {
  challenge: Pick<
    Challenge,
    "id" | "title" | "state" | "period_start" | "period_kind" | "period_length"
  >;
  timeZone: string;
  open: boolean;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const schedule = useSchedule(challenge.id);
  const moving = challenge.state === "chosen";
  const { period_kind: kind, period_length: length } = challenge;
  const today = todayIn(timeZone);
  const tomorrow = addDays(today, 1);
  const options = startOptions(kind, length, today).filter(
    (option) => option.periodStart !== challenge.period_start,
  );
  const [picked, setPicked] = useState<string | null>(null);
  // Default: the first whole month or week, or tomorrow for a number of days.
  const firstWhole = options.find((option) => option.startsOn === option.periodStart);
  const value =
    picked ?? (kind === "day" ? tomorrow : (firstWhole?.periodStart ?? options[0]?.periodStart));
  const day = (date: string) => formatDay(date, i18n.language);
  const when = (start: string) =>
    kind === "month"
      ? { key: "Month", values: { month: monthName(start, i18n.language) } }
      : { key: "From", values: { date: day(start) } };

  const confirm = () => {
    if (!value) return;
    schedule.mutate(value, {
      onSuccess: () => {
        const { key, values } = when(value);
        toast(t(`challenges.schedule.done${key}`, values), "success");
        onClose();
      },
    });
  };

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
      {kind === "day" ? (
        <TextField
          type="date"
          label={t("challenges.schedule.firstDay")}
          hint={
            value
              ? t("challenges.schedule.until", { date: day(periodEnd(kind, value, length)) })
              : undefined
          }
          min={tomorrow}
          value={value ?? ""}
          onChange={(e) => setPicked(e.target.value)}
        />
      ) : (
        <OptionList
          label={t(kind === "month" ? "challenges.schedule.month" : "challenges.schedule.week")}
          value={value ?? ""}
          onChange={setPicked}
          options={options.map((option) => ({
            value: option.periodStart,
            title:
              kind === "month"
                ? monthAndYear(option.periodStart, i18n.language)
                : t("challenges.schedule.weekOf", { date: day(option.periodStart) }),
            description:
              option.startsOn === option.periodStart
                ? t("challenges.range", { from: day(option.startsOn), to: day(option.endsOn) })
                : t("challenges.schedule.fromTomorrow", {
                    date: day(option.startsOn),
                    to: day(option.endsOn),
                  }),
          }))}
        />
      )}
      <p className={styles.muted}>
        {moving ? t("challenges.schedule.moveBody") : t("challenges.schedule.body")}
      </p>
      {schedule.error && <Banner tone="danger" title={errorMessage(t, schedule.error)} />}
      <div className={styles.actions}>
        <Button
          size="lg"
          fullWidth
          loading={schedule.isPending}
          disabled={!value}
          onClick={confirm}
        >
          {value
            ? t(`challenges.schedule.confirm${when(value).key}`, when(value).values)
            : t("challenges.schedule.open")}
        </Button>
        <Button variant="secondary" size="lg" fullWidth onClick={onClose}>
          {t("common.cancel")}
        </Button>
      </div>
    </Sheet>
  );
}
