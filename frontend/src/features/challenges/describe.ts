import type { TFunction } from "i18next";

import type { IconName } from "@/shared/ui";

import type { Challenge, ChallengeInput } from "./api";

type Shape = Pick<
  Challenge,
  | "measure"
  | "unit"
  | "frequency"
  | "weekdays"
  | "times"
  | "target_scope"
  | "target_value"
  | "proof_kind"
  | "proof_required"
>;

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

/** "Every day", "On Mon, Wed, Fri", "3 times a week", ... */
export function describeFrequency(
  t: TFunction,
  shape: Pick<Shape, "frequency" | "weekdays" | "times">,
) {
  switch (shape.frequency) {
    case "weekdays":
      return t("challenges.describe.weekdays", {
        days: shape.weekdays.map((day) => t(`challenges.days.abbr.${day}`)).join(", "),
      });
    case "times_per_week":
      return shape.times === 1
        ? t("challenges.describe.oncePerWeek")
        : t("challenges.describe.timesPerWeek", { n: shape.times ?? 0 });
    case "times_per_period":
      return shape.times === 1
        ? t("challenges.describe.oncePerPeriod")
        : t("challenges.describe.timesPerPeriod", { n: shape.times ?? 0 });
    case "once":
      return t("challenges.describe.once");
    default:
      return t("challenges.describe.daily");
  }
}

/** "Just a check-in", "A number (km)", "Holding back" */
export function describeMeasure(t: TFunction, shape: Pick<Shape, "measure" | "unit">) {
  if (shape.measure === "quantity") return t("challenges.describe.quantity", { unit: shape.unit });
  if (shape.measure === "abstain") return t("challenges.describe.abstain");
  return t("challenges.describe.check");
}

/** "At least 50 push-ups each time", or null without a target. */
export function describeTarget(
  t: TFunction,
  shape: Pick<Shape, "target_scope" | "target_value" | "unit">,
  language: string,
) {
  if (shape.target_scope === "none" || shape.target_value == null) return null;
  const value = new Intl.NumberFormat(language).format(Number(shape.target_value));
  return t(`challenges.describe.target.${shape.target_scope}`, { value, unit: shape.unit });
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

/** One short line for lists: "Every day · 50 push-ups each time · Video". */
export function summaryLine(t: TFunction, shape: Shape, language: string) {
  return [
    describeFrequency(t, shape),
    describeTarget(t, shape, language) ?? describeMeasure(t, shape),
    describeProof(t, shape),
  ].join(" · ");
}
