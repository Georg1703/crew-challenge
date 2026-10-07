import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Member } from "@/api";
import { useMe } from "@/features/auth";
import { errorMessage } from "@/i18n/errors";
import { formatList } from "@/shared/lib/format";
import {
  Button,
  EmojiPicker,
  Icon,
  ReactionChips,
  ReactionMenu,
  Sheet,
  useToast,
  type EmojiPickerTexts,
  type ReactionChip,
} from "@/shared/ui";

import { QUICK_REACTIONS, useReact, type ReactionSummary, type ReactionTarget } from "../api";
import styles from "../reactions.module.css";
import { ReactorsSheet } from "./ReactorsSheet";

/**
 * Reactions on anything registered as a target: the chips, the react button with its quick row,
 * the full emoji picker and who reacted. The owner of the data passes the target's `summary` and
 * keeps it fresh through `onChange` (optimistic, then the server's answer).
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
  const opener = useRef<HTMLButtonElement>(null);
  const react = useReact({
    target,
    id,
    me,
    summary,
    onChange,
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  const byId = useMemo(() => new Map(people.map((m) => [m.id, m])), [people]);
  const texts = useMemo(() => pickerTexts(t), [t]);

  const name = (memberId: string) =>
    memberId === me ? t("reactions.you") : (byId.get(memberId)?.display_name ?? "?");
  const chips: ReactionChip[] = summary.groups.map((group) => ({
    emoji: group.emoji,
    mine: group.emoji === summary.mine,
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
  const choose = (emoji: string) => react.mutate(emoji === summary.mine ? null : emoji);

  return (
    <div className={styles.row}>
      <ReactionChips chips={chips} onToggle={choose} onHold={(emoji) => setWho(emoji)} />
      <span className={styles.anchor}>
        <Button
          ref={opener}
          variant="ghost"
          icon={<Icon name="smilePlus" size={20} />}
          aria-label={t("reactions.react")}
          aria-expanded={menu}
          onClick={() => setMenu((open) => !open)}
        />
        <ReactionMenu
          open={menu}
          onClose={() => setMenu(false)}
          label={t("reactions.react")}
          emojis={QUICK_REACTIONS}
          selected={summary.mine}
          onPick={choose}
          moreLabel={t("reactions.more")}
          onMore={() => setPicker(true)}
          whoLabel={summary.groups.length > 0 ? t("reactions.who") : undefined}
          onWho={summary.groups.length > 0 ? () => setWho("") : undefined}
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
            react.mutate(emoji === summary.mine ? null : emoji);
          }}
        />
      </Sheet>
      <ReactorsSheet
        open={who !== null}
        onClose={() => setWho(null)}
        summary={summary}
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
