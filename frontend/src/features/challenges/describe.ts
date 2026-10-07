import type { TFunction } from "i18next";

import type { IconName } from "@/shared/ui";

import type { Challenge, ChallengeInput } from "./api";

/** A challenge as stored, or as the wizard is about to send it (numbers as text). */
type Shape = Pick<
  Challenge,
  | "measure"
  | "unit"
  | "window"
  | "on_days"
  | "need_kind"
  | "period_kind"
  | "period_length"
  | "proof_kind"
  | "proof_required"
> & { need_value: number | string; day_min: number | string | null };

/** "1 month", "4 weeks", "21 days" */
export function describeLength(t: TFunction, shape: Pick<Shape, "period_kind" | "period_length">) {
  return t(`challenges.length.${shape.period_kind}`, { count: shape.period_length });
}

/** Challenge icon keys (from the API) mapped to the shared icon set. */
export const CHALLENGE_ICONS: Record<ChallengeInput["icon"], IconName> = {
  dumbbell: "dumbbell",
  running: "activity",
  book: "book",
  water: "droplet",
  sugar: "cookie",
  phone: "phone",
  sleep: "moon",
  walk: "mountain",
  meditate: "heart",
  food: "apple",
  money: "wallet",
  star: "star",
};

export const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;

export function weekdayShort(t: TFunction, day: number): string {
  return t(`challenges.days.short.${day}`);
}

/** "the month", "4 weeks", "21 days": what a whole-period rule is counted over. */
export function describePeriod(t: TFunction, shape: Pick<Shape, "period_kind" | "period_length">) {
  return t(`challenges.describe.period.${shape.period_kind}`, { count: shape.period_length });
}

/** "Every day", "On Mon, Wed, Fri", "3 times a week", "8 times in 4 weeks", "50 km a week", ... */
export function describeRule(
  t: TFunction,
  shape: Pick<
    Shape,
    "window" | "on_days" | "need_kind" | "need_value" | "unit" | "period_kind" | "period_length"
  >,
  language: string,
) {
  const n = Number(shape.need_value);
  const period = describePeriod(t, shape);
  if (shape.need_kind === "amount") {
    const value = new Intl.NumberFormat(language).format(n);
    if (shape.window === "week")
      return t("challenges.describe.totalPerWeek", { value, unit: shape.unit });
    if (shape.window === "month")
      return t("challenges.describe.totalPerMonth", { value, unit: shape.unit });
    return t("challenges.describe.totalPerPeriod", { value, unit: shape.unit, period });
  }
  if (shape.window === "week")
    return n === 1
      ? t("challenges.describe.oncePerWeek")
      : t("challenges.describe.timesPerWeek", { n });
  if (shape.window === "month")
    return n === 1
      ? t("challenges.describe.oncePerMonth")
      : t("challenges.describe.timesPerMonth", { n });
  if (shape.window === "period")
    return n === 1
      ? t("challenges.describe.once")
      : t("challenges.describe.timesPerPeriod", { n, period });
  if (shape.on_days.length)
    return t("challenges.describe.weekdays", {
      days: shape.on_days.map((day) => t(`challenges.days.abbr.${day}`)).join(", "),
    });
  return t("challenges.describe.daily");
}

/** "Just a check-in", "A number (km)", "Holding back" */
export function describeMeasure(t: TFunction, shape: Pick<Shape, "measure" | "unit">) {
  if (shape.measure === "quantity") return t("challenges.describe.quantity", { unit: shape.unit });
  if (shape.measure === "abstain") return t("challenges.describe.abstain");
  return t("challenges.describe.check");
}

/** "At least 50 push-ups each check-in", or null without a minimum. */
export function describeDayMin(
  t: TFunction,
  shape: Pick<Shape, "day_min" | "unit">,
  language: string,
) {
  if (shape.day_min == null) return null;
  const value = new Intl.NumberFormat(language).format(Number(shape.day_min));
  return t("challenges.describe.dayMin", { value, unit: shape.unit });
}

/** "Video, required", "No proof" */
export function describeProof(t: TFunction, shape: Pick<Shape, "proof_kind" | "proof_required">) {
  if (shape.proof_kind === "none") return t("challenges.describe.proof.none");
  return t(
    shape.proof_required
      ? "challenges.describe.proofRequired"
      : "challenges.describe.proofOptional",
    {
      kind: t(`challenges.describe.proof.${shape.proof_kind}`),
    },
  );
}

/** One short line for lists: "1 month · Every day · 50 push-ups each check-in · Video". */
export function summaryLine(t: TFunction, shape: Shape, language: string) {
  return [
    describeLength(t, shape),
    describeRule(t, shape, language),
    describeDayMin(t, shape, language) ?? describeMeasure(t, shape),
    describeProof(t, shape),
  ].join(" · ");
}
