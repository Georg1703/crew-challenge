import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { isApiError } from "@/api";
import { useMe } from "@/features/auth";
import { useCrew } from "@/features/crew";
import { errorMessage } from "@/i18n/errors";
import { formatList } from "@/shared/lib/format";
import {
  Banner,
  Button,
  ChipGroup,
  IconPicker,
  OptionList,
  Screen,
  Skeleton,
  Stack,
  StepProgress,
  Stepper,
  TextArea,
  TextField,
  Toggle,
  useToast,
} from "@/shared/ui";

import {
  useChallenge,
  useEditChallenge,
  useProposeChallenge,
  type Challenge,
  type ChallengeInput,
} from "../api";
import styles from "../challenges.module.css";
import { ParticipantPicker } from "../components/ParticipantPicker";
import {
  CHALLENGE_ICONS,
  WEEKDAYS,
  describeDayMin,
  describeMeasure,
  describeProof,
  describeRule,
  weekdayShort,
} from "../describe";

/** How often, as the wizard offers it: counted check-ins, or (numbers only) a total. */
const COUNTED = ["daily", "weekdays", "times_per_week", "times_per_period", "once"] as const;
const TOTALS = ["total_per_week", "total_per_period"] as const;
type Often = (typeof COUNTED)[number] | (typeof TOTALS)[number];

type Draft = Required<
  Pick<
    ChallengeInput,
    "title" | "rules" | "icon" | "measure" | "unit" | "proof_kind" | "proof_required"
  >
> & {
  often: Often;
  on_days: number[];
  times: number;
  /** Numbers as typed ("12,5"), sent with a dot. */
  total: string;
  day_min: string;
  /** null: nobody changed the list yet, so the whole crew takes part. */
  participant_ids: string[] | null;
};

const EMPTY: Draft = {
  title: "",
  rules: "",
  icon: "star",
  measure: "check",
  unit: "",
  often: "daily",
  on_days: [0, 1, 2, 3, 4],
  times: 3,
  total: "",
  day_min: "",
  proof_kind: "none",
  proof_required: false,
  participant_ids: null,
};

const STEPS = ["what", "who", "record", "often", "proof", "review"] as const;
type Step = (typeof STEPS)[number];

/** Which step shows each field, to send people back to the field the server rejected. */
const FIELD_STEP: Record<string, Step> = {
  title: "what",
  rules: "what",
  icon: "what",
  participant_ids: "who",
  measure: "record",
  unit: "record",
  window: "often",
  on_days: "often",
  need_kind: "often",
  need_value: "often",
  day_min: "often",
  proof_kind: "proof",
  proof_required: "proof",
};

/** A typed number as the API takes it: "12,5" -> "12.5". */
const decimal = (text: string) => text.trim().replace(",", ".");

const isTotal = (often: Often) => often === "total_per_week" || often === "total_per_period";

type Rule = Pick<ChallengeInput, "window" | "on_days" | "need_kind" | "need_value">;

/** The window and need behind a choice in "How often?". */
function rule(draft: Draft): Rule {
  const counted = (window: Rule["window"], n: number): Rule => ({
    window,
    on_days: [],
    need_kind: "count",
    need_value: String(n),
  });
  const total = (window: Rule["window"]): Rule => ({
    window,
    on_days: [],
    need_kind: "amount",
    need_value: decimal(draft.total),
  });
  switch (draft.often) {
    case "weekdays":
      return { ...counted("day", 1), on_days: draft.on_days };
    case "times_per_week":
      return counted("week", draft.times);
    case "times_per_period":
      return counted("period", draft.times);
    case "once":
      return counted("period", 1);
    case "total_per_week":
      return total("week");
    case "total_per_period":
      return total("period");
    default:
      return counted("day", 1);
  }
}

/** The choice in "How often?" for a stored challenge. */
function oftenOf(c: Challenge): Often {
  if (c.need_kind === "amount") return c.window === "week" ? "total_per_week" : "total_per_period";
  if (c.window === "week") return "times_per_week";
  if (c.window === "period") return c.need_value === 1 ? "once" : "times_per_period";
  return c.on_days.length ? "weekdays" : "daily";
}

function toInput(draft: Draft): ChallengeInput {
  const quantity = draft.measure === "quantity";
  const shape = rule(draft);
  const dayMin = quantity && shape.need_kind === "count" && draft.day_min.trim();
  return {
    title: draft.title,
    rules: draft.rules,
    icon: draft.icon,
    measure: draft.measure,
    unit: quantity ? draft.unit : "",
    ...shape,
    day_min: dayMin ? decimal(draft.day_min) : null,
    proof_kind: draft.proof_kind,
    proof_required: draft.proof_kind !== "none" && draft.proof_required,
    ...(draft.participant_ids ? { participant_ids: draft.participant_ids } : {}),
  };
}

/** /challenges/new and /challenges/:id/edit */
export function ProposeRoute() {
  const { id } = useParams();
  return id ? <EditProposal id={id} /> : <ProposeWizard initial={EMPTY} />;
}

function EditProposal({ id }: { id: string }) {
  const { t } = useTranslation();
  const challenge = useChallenge(id);
  if (challenge.isPending) {
    return (
      <Screen withTabBar={false}>
        <Skeleton lines={5} />
      </Screen>
    );
  }
  if (!challenge.data) {
    return (
      <Screen withTabBar={false} title={t("challenges.title")}>
        <Banner tone="danger" title={errorMessage(t, challenge.error)} />
      </Screen>
    );
  }
  const c = challenge.data;
  return (
    <ProposeWizard
      editingId={id}
      initial={{
        title: c.title,
        rules: c.rules,
        icon: c.icon,
        measure: c.measure,
        unit: c.unit,
        often: oftenOf(c),
        on_days: c.on_days.length ? c.on_days : EMPTY.on_days,
        times: c.need_kind === "count" && c.window !== "day" ? c.need_value : EMPTY.times,
        total: c.need_kind === "amount" ? String(c.need_value) : "",
        day_min: c.day_min == null ? "" : String(c.day_min),
        proof_kind: c.proof_kind,
        proof_required: c.proof_required,
        participant_ids: c.participants.map((p) => p.member.id),
      }}
    />
  );
}

function ProposeWizard({ initial, editingId }: { initial: Draft; editingId?: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const me = useMe();
  const crew = useCrew();
  const propose = useProposeChallenge();
  const edit = useEditChallenge(editingId ?? "");
  const save = editingId ? edit : propose;
  const [draft, setDraft] = useState<Draft>(initial);
  const [step, setStep] = useState<Step>("what");
  const [localErrors, setLocalErrors] = useState<Record<string, string>>({});

  const index = STEPS.indexOf(step);
  const apiError = isApiError(save.error) ? save.error : undefined;
  const fieldError = (name: string) => localErrors[name] ?? apiError?.field(name);
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const quantity = draft.measure === "quantity";
  /** Totals need numbers: another kind of record goes back to "every day". */
  const setMeasure = (measure: Draft["measure"]) =>
    setDraft((current) => ({
      ...current,
      measure,
      often: measure !== "quantity" && isTotal(current.often) ? "daily" : current.often,
    }));
  const people = crew.data?.members ?? [];
  const creatorId = me.data?.member?.id; // only the creator proposes or edits

  /** The checks a person needs before moving on; the server checks everything again. */
  const check = (current: Step): Record<string, string> => {
    const errors: Record<string, string> = {};
    if (current === "what" && !draft.title.trim()) errors.title = t("challenges.errors.title");
    if (current === "record" && quantity && !draft.unit.trim())
      errors.unit = t("challenges.errors.unit");
    if (current === "often") {
      if (draft.often === "weekdays" && !draft.on_days.length)
        errors.on_days = t("challenges.errors.onDays");
      if (isTotal(draft.often) && !(Number(decimal(draft.total)) > 0))
        errors.need_value = t("challenges.errors.number");
      if (quantity && draft.day_min.trim() && !(Number(decimal(draft.day_min)) > 0))
        errors.day_min = t("challenges.errors.number");
    }
    return errors;
  };

  const next = (event: FormEvent) => {
    event.preventDefault();
    const errors = check(step);
    setLocalErrors(errors);
    if (Object.keys(errors).length) return;
    if (step !== "review") return setStep(STEPS[index + 1] ?? "review");
    save.mutate(toInput(draft), {
      onSuccess: (challenge) => {
        toast(editingId ? t("challenges.saved") : t("challenges.published"), "success");
        navigate(`/challenges/${challenge.id}`, { replace: true });
      },
      onError: (error) => {
        const field = isApiError(error) ? Object.keys(error.fields ?? {})[0] : undefined;
        if (field && FIELD_STEP[field]) setStep(FIELD_STEP[field]);
      },
    });
  };

  const back = () => (index === 0 ? navigate(-1) : setStep(STEPS[index - 1] ?? "what"));
  const generalError =
    save.error && !Object.keys(apiError?.fields ?? {}).length ? errorMessage(t, save.error) : null;

  return (
    <Screen withTabBar={false} title={t(`challenges.steps.${step}.title`)}>
      <div className={styles.wizardTop}>
        <StepProgress
          current={index + 1}
          total={STEPS.length}
          label={t("challenges.stepLabel", { n: index + 1, total: STEPS.length })}
        />
        <p className={styles.meta}>
          {editingId ? t("challenges.editingNote") : t("challenges.proposingNote")}
        </p>
      </div>
      {generalError && <Banner tone="danger" title={generalError} />}

      <form onSubmit={next} noValidate>
        <Stack gap="lg">
          {step === "what" && (
            <Stack>
              <TextField
                label={t("challenges.fields.title")}
                hint={t("challenges.fields.titleHint")}
                maxLength={60}
                value={draft.title}
                onChange={(e) => set("title", e.target.value)}
                error={fieldError("title")}
              />
              <IconPicker
                label={t("challenges.fields.icon")}
                value={draft.icon}
                onChange={(icon) => set("icon", icon)}
                options={(Object.keys(CHALLENGE_ICONS) as Draft["icon"][]).map((key) => ({
                  value: key,
                  icon: CHALLENGE_ICONS[key],
                  name: t(`challenges.icons.${key}`),
                }))}
              />
              <TextArea
                label={t("challenges.fields.rules")}
                hint={t("challenges.fields.rulesHint")}
                maxLength={500}
                value={draft.rules}
                onChange={(e) => set("rules", e.target.value)}
                error={fieldError("rules")}
              />
            </Stack>
          )}

          {step === "who" &&
            (crew.data ? (
              <ParticipantPicker
                people={people}
                creatorId={creatorId}
                values={draft.participant_ids ?? people.map((person) => person.id)}
                onChange={(ids) => set("participant_ids", ids)}
                error={fieldError("participant_ids")}
              />
            ) : (
              <Skeleton lines={4} />
            ))}

          {step === "record" && (
            <Stack>
              <OptionList
                label={t("challenges.fields.measure")}
                value={draft.measure}
                onChange={setMeasure}
                options={(["check", "quantity", "abstain"] as const).map((value) => ({
                  value,
                  title: t(`challenges.options.measure.${value}.title`),
                  description: t(`challenges.options.measure.${value}.description`),
                }))}
              />
              {quantity && (
                <TextField
                  label={t("challenges.fields.unit")}
                  hint={t("challenges.fields.unitHint")}
                  maxLength={20}
                  value={draft.unit}
                  onChange={(e) => set("unit", e.target.value)}
                  error={fieldError("unit")}
                />
              )}
            </Stack>
          )}

          {step === "often" && (
            <Stack>
              <OptionList
                label={t("challenges.fields.often")}
                value={draft.often}
                onChange={(often) => set("often", often)}
                options={(quantity ? [...COUNTED, ...TOTALS] : COUNTED).map((value) => ({
                  value,
                  title: t(`challenges.options.often.${value}.title`),
                  description: t(`challenges.options.often.${value}.description`),
                }))}
              />
              {draft.often === "weekdays" && (
                <ChipGroup
                  label={t("challenges.fields.onDays")}
                  values={draft.on_days}
                  onChange={(days) => set("on_days", [...days].sort())}
                  error={fieldError("on_days")}
                  options={WEEKDAYS.map((day) => ({
                    value: day,
                    label: weekdayShort(t, day),
                    name: t(`challenges.days.long.${day}`),
                  }))}
                />
              )}
              {(draft.often === "times_per_week" || draft.often === "times_per_period") && (
                <Stepper
                  label={t("challenges.fields.times")}
                  value={draft.times}
                  min={1}
                  max={draft.often === "times_per_week" ? 7 : 31}
                  onChange={(times) => set("times", times)}
                  decreaseLabel={t("challenges.fields.fewer")}
                  increaseLabel={t("challenges.fields.more")}
                />
              )}
              {isTotal(draft.often) ? (
                <TextField
                  label={t("challenges.fields.total", { unit: draft.unit })}
                  inputMode="decimal"
                  value={draft.total}
                  onChange={(e) => set("total", e.target.value)}
                  error={fieldError("need_value")}
                />
              ) : (
                quantity && (
                  <TextField
                    label={t("challenges.fields.dayMin", { unit: draft.unit })}
                    hint={t("challenges.fields.dayMinHint")}
                    inputMode="decimal"
                    value={draft.day_min}
                    onChange={(e) => set("day_min", e.target.value)}
                    error={fieldError("day_min")}
                  />
                )
              )}
            </Stack>
          )}

          {step === "proof" && (
            <Stack>
              <OptionList
                label={t("challenges.fields.proof")}
                value={draft.proof_kind}
                onChange={(kind) => set("proof_kind", kind)}
                options={(["none", "photo", "video", "photo_or_video"] as const).map((value) => ({
                  value,
                  title: t(`challenges.options.proof.${value}.title`),
                  description: t(`challenges.options.proof.${value}.description`),
                }))}
              />
              {draft.proof_kind !== "none" && (
                <Toggle
                  label={t("challenges.fields.proofRequired")}
                  description={t("challenges.fields.proofRequiredHint")}
                  checked={draft.proof_required}
                  onChange={(on) => set("proof_required", on)}
                />
              )}
            </Stack>
          )}

          {step === "review" && (
            <Review draft={draft} editing={Boolean(editingId)} people={people} />
          )}

          <div className={styles.wizardNav}>
            <Button variant="secondary" size="lg" onClick={back}>
              {t("challenges.back")}
            </Button>
            <Button type="submit" size="lg" loading={save.isPending}>
              {step === "review"
                ? editingId
                  ? t("challenges.save")
                  : t("challenges.publish")
                : t("challenges.next")}
            </Button>
          </div>
        </Stack>
      </form>
    </Screen>
  );
}

function Review({
  draft,
  editing,
  people,
}: {
  draft: Draft;
  editing: boolean;
  people: { id: string; display_name: string }[];
}) {
  const { t, i18n } = useTranslation();
  const input = toInput(draft);
  const shape = { ...input, on_days: input.on_days ?? [], day_min: input.day_min ?? null };
  const dayMin = describeDayMin(t, shape, i18n.language);
  /** "The whole crew", a few names, or "18 of 20" when many. */
  const whoSummary = (ids: string[] | null, crew: { id: string; display_name: string }[]) => {
    const chosen = crew.filter((person) => !ids || ids.includes(person.id));
    if (chosen.length >= crew.length) return t("challenges.who.everyone");
    if (chosen.length > 5)
      return t("challenges.who.short", { n: chosen.length, total: crew.length });
    return formatList(
      chosen.map((person) => person.display_name),
      i18n.language,
    );
  };
  const facts: [string, string][] = [
    [t("challenges.facts.name"), draft.title.trim()],
    [t("challenges.facts.who"), whoSummary(draft.participant_ids, people)],
    [t("challenges.facts.record"), describeMeasure(t, shape)],
    [t("challenges.facts.often"), describeRule(t, shape, i18n.language)],
    ...(dayMin ? [[t("challenges.facts.target"), dayMin] as [string, string]] : []),
    [t("challenges.facts.proof"), describeProof(t, shape)],
  ];
  return (
    <Stack>
      <dl className={styles.facts}>
        {facts.map(([label, value]) => (
          <div key={label} className={styles.factRow}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {draft.rules.trim() && <p className={styles.muted}>{draft.rules.trim()}</p>}
      <p className={styles.meta}>
        {editing ? t("challenges.editResetsVotes") : t("challenges.reviewNote")}
      </p>
    </Stack>
  );
}
