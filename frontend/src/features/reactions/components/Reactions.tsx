import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { useMe } from "@/features/auth";
import { errorMessage } from "@/i18n/errors";
import { formatList } from "@/shared/lib/format";
import { holdOn } from "@/shared/lib/usePress";
import { useReducedMotion } from "@/shared/motion";
import {
  Button,
  EmojiFlight,
  EmojiPicker,
  Icon,
  ReactionChips,
  ReactionMenu,
  Sheet,
  preloadEmojiPicker,
  useToast,
  type EmojiPickerTexts,
  type Flight,
  type ReactionChip,
} from "@/shared/ui";

import { QUICK_REACTIONS, useReact, type ReactionSummary, type ReactionTarget } from "../api";
import styles from "../reactions.module.css";
import { ReactorsSheet } from "./ReactorsSheet";

/**
 * Reactions on anything registered as a target: the chips, the react button with its quick row,
 * the full emoji picker and who reacted. On a phone, holding the card it sits in opens the quick
 * row too. The owner of the data passes the target's `summary`; the
 * change shows here at once (with the picked emoji flying over the card into its chip), and
 * `onChange` gets the server's answer for the owner's cache, without redrawing the owner on every
 * tap.
 */
export function Reactions({
  target,
  id,
  summary,
  people,
  onChange,
}: {
  target: ReactionTarget;
  id: string;
  summary: ReactionSummary;
  /** The crew's members: names and avatars for the ids in the summary. */
  people: Member[];
  onChange: (summary: ReactionSummary) => void;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const me = useMe().data?.member?.id ?? "";
  const [menu, setMenu] = useState(false);
  const [picker, setPicker] = useState(false);
  const [who, setWho] = useState<string | null>(null); // the emoji to list first, "" for all
  const [flight, setFlight] = useState<Flight | null>(null);
  const [landing, setLanding] = useState<string | null>(null); // a new chip, shown on arrival
  const opener = useRef<HTMLButtonElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const still = useReducedMotion();
  // What this card shows: the owner's summary, changed at once by a tap. A new summary from the
  // owner (a refresh, the server's answer) replaces it.
  const [shown, setShown] = useState(summary);
  const [given, setGiven] = useState(summary);
  if (summary !== given) {
    setGiven(summary);
    setShown(summary);
  }
  const react = useReact({
    target,
    id,
    me,
    summary: shown,
    onChange: setShown,
    onSaved: (answer) => startTransition(() => onChange(answer)), // the owner redraws when idle
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  useEffect(() => {
    const card = root.current?.closest("article");
    if (!card) return;
    return holdOn(
      card,
      () => {
        preloadEmojiPicker();
        setMenu(true);
      },
      { skip: root.current },
    );
  }, []);
  const byId = useMemo(() => new Map(people.map((m) => [m.id, m])), [people]);
  const texts = useMemo(() => pickerTexts(t), [t]);

  const name = (memberId: string) =>
    memberId === me ? t("reactions.you") : (byId.get(memberId)?.display_name ?? "?");
  const chips: ReactionChip[] = shown.groups.map((group) => ({
    emoji: group.emoji,
    mine: group.emoji === shown.mine,
    people: group.member_ids.map((memberId) => ({
      id: memberId,
      name: byId.get(memberId)?.display_name ?? "?",
      seed: byId.get(memberId)?.avatar_seed ?? memberId,
    })),
    label: t("reactions.chip", {
      emoji: group.emoji,
      names: formatList(group.member_ids.map(name), i18n.language),
    }),
  }));
  /** React (or take it back), and fly the new emoji from `from` over the card into its chip. */
  const choose = (emoji: string, from?: DOMRect) => {
    const next = emoji === shown.mine ? null : emoji;
    const isNew = next !== null && !shown.groups.some((group) => group.emoji === next);
    react.mutate(next);
    const card = root.current?.closest("article");
    const via = (card?.querySelector("[data-stage]") ?? card)?.getBoundingClientRect();
    const start = from ?? opener.current?.getBoundingClientRect();
    if (!next || still || !via || !start) return;
    setLanding(isNew ? next : null);
    setFlight({
      id: Date.now(),
      emoji: next,
      from: start,
      via,
      to: () =>
        root.current
          ?.querySelector(`[data-emoji="${CSS.escape(next)}"]`)
          ?.getBoundingClientRect() ?? null,
    });
  };

  return (
    <div ref={root} className={styles.row}>
      <ReactionChips
        chips={chips}
        onToggle={choose}
        onHold={(emoji) => setWho(emoji)}
        landing={flight ? landing : null}
      />
      {flight && (
        <EmojiFlight
          key={flight.id}
          flight={flight}
          onDone={() => {
            setFlight(null);
            setLanding(null);
          }}
        />
      )}
      <span className={styles.anchor}>
        <Button
          ref={opener}
          variant="ghost"
          className={styles.react}
          icon={<Icon name="smilePlus" size={18} />}
          aria-label={t("reactions.react")}
          aria-expanded={menu}
          onClick={() => {
            if (!menu) preloadEmojiPicker(); // so "+" opens at once
            setMenu((open) => !open);
          }}
        />
        <ReactionMenu
          open={menu}
          onClose={() => setMenu(false)}
          label={t("reactions.react")}
          emojis={QUICK_REACTIONS}
          selected={shown.mine}
          onPick={choose}
          moreLabel={t("reactions.more")}
          onMore={() => setPicker(true)}
          whoLabel={shown.groups.length > 0 ? t("reactions.who") : undefined}
          onWho={shown.groups.length > 0 ? () => setWho("") : undefined}
          anchor={opener}
        />
      </span>
      <Sheet
        open={picker}
        onClose={() => setPicker(false)}
        title={t("reactions.pick")}
        closeLabel={t("common.close")}
      >
        <EmojiPicker
          texts={texts}
          errorText={t("reactions.pickerFailed")}
          retryLabel={t("common.retry")}
          onPick={(emoji) => {
            setPicker(false);
            choose(emoji);
          }}
        />
      </Sheet>
      <ReactorsSheet
        open={who !== null}
        onClose={() => setWho(null)}
        summary={shown}
        first={who || null}
        people={byId}
        me={me}
      />
    </div>
  );
}

function pickerTexts(t: ReturnType<typeof useTranslation>["t"]): EmojiPickerTexts {
  const categories = [
    "activity",
    "custom",
    "flags",
    "foods",
    "frequent",
    "nature",
    "objects",
    "people",
    "places",
    "search",
    "symbols",
  ] as const;
  const skins = ["choose", "1", "2", "3", "4", "5", "6"] as const;
  return {
    search: t("reactions.picker.search"),
    search_no_results_1: t("reactions.picker.noResults"),
    search_no_results_2: t("reactions.picker.noResultsHint"),
    pick: t("reactions.pick"),
    add_custom: t("reactions.picker.addCustom"),
    categories: Object.fromEntries(
      categories.map((key) => [key, t(`reactions.picker.categories.${key}`)]),
    ) as EmojiPickerTexts["categories"],
    skins: Object.fromEntries(
      skins.map((key) => [key, t(`reactions.picker.skins.${key}`)]),
    ) as EmojiPickerTexts["skins"],
  };
}
