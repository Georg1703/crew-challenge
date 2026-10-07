import type { TFunction } from "i18next";

import { weekday } from "@/shared/lib/dates";
import { formatDay, formatNumber } from "@/shared/lib/format";

import type { TodayChallenge, Window } from "./api";

/** What decides how a challenge's windows read (a Today card and a challenge both have it). */
export type WindowRule = Pick<TodayChallenge, "window" | "need_kind" | "unit">;

/** The key word for a challenge's windows: a day window has none (it is judged day by day). */
export const windowKind = (rule: WindowRule) =>
  rule.window === "week" || rule.window === "month" ? rule.window : "period";

/** "Thu - Sun" for a week by weekday names, "5 November - 30 November" by dates; one day alone. */
export function windowDays(
  t: TFunction,
  w: Pick<Window, "first" | "last">,
  language: string,
  weekdays = false,
): string {
  const name = (day: string) =>
    weekdays ? t(`challenges.days.abbr.${weekday(day)}`) : formatDay(day, language);
  return w.first === w.last
    ? name(w.first)
    : t("challenges.range", { from: name(w.first), to: name(w.last) });
}

/** "2" (check-ins) or "35 km". */
export function windowAmount(t: TFunction, value: number, rule: WindowRule, language: string) {
  const number = formatNumber(value, language);
  return rule.need_kind === "amount"
    ? t("windows.amount", { value: number, unit: rule.unit })
    : number;
}

/**
 * "Short week: Thu - Sun, 2 instead of 3", or null for a window that asks for the full need.
 * `phrase` "leave" says it as what leaving today would make of the last window.
 */
export function shortWindow(
  t: TFunction,
  w: Window,
  rule: WindowRule,
  language: string,
  phrase: "short" | "leave" = "short",
): string | null {
  if (w.need >= w.full_need) return null;
  return t(`windows.${phrase}.${windowKind(rule)}`, {
    days: windowDays(t, w, language, rule.window === "week"),
    need: windowAmount(t, w.need, rule, language),
    full: windowAmount(t, w.full_need, rule, language),
  });
}
