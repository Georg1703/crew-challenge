import type { TFunction } from "i18next";

import { periodEnd } from "@/shared/lib/dates";
import { formatDay, formatDayLong, formatNumber, monthAndYear } from "@/shared/lib/format";

import type { Spin } from "./api";

type Failed = Pick<Spin, "window_first" | "window_last" | "need" | "done" | "need_kind"> & {
  challenge: Pick<Spin["challenge"], "unit">;
};

/**
 * What failed: "Missed Tuesday, October 6", "October 5 - October 11: 1 of 3", "October 2026: 30 km
 * of 50 km". Only a whole calendar month is named as one; any other window by its days.
 */
export function describeFailed(t: TFunction, spin: Failed, language: string): string {
  const { window_first: first, window_last: last } = spin;
  if (first === last) return t("doom.missedDay", { date: formatDayLong(first, language) });
  const amount = (value: number) =>
    spin.need_kind === "amount"
      ? t("windows.amount", { value: formatNumber(value, language), unit: spin.challenge.unit })
      : formatNumber(value, language);
  const whole = first.endsWith("-01") && last === periodEnd("month", first, 1);
  const when = whole
    ? monthAndYear(first, language)
    : t("challenges.range", { from: formatDay(first, language), to: formatDay(last, language) });
  return t("doom.windowShort", { when, done: amount(spin.done), need: amount(spin.need) });
}
