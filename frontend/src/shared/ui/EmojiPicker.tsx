import { useCallback, useEffect, useRef, useState } from "react";

import { Banner } from "./Banner";
import { Button } from "./Button";
import styles from "./EmojiPicker.module.css";
import { Skeleton } from "./Skeleton";

/** Emoji Mart's texts (its own i18n shape); the caller fills them from our translations. */
export interface EmojiPickerTexts {
  search: string;
  search_no_results_1: string;
  search_no_results_2: string;
  pick: string;
  add_custom: string;
  categories: Record<
    | "activity"
    | "custom"
    | "flags"
    | "foods"
    | "frequent"
    | "nature"
    | "objects"
    | "people"
    | "places"
    | "search"
    | "symbols",
    string
  >;
  skins: Record<"choose" | "1" | "2" | "3" | "4" | "5" | "6", string>;
}

/** Loaded on first use only (~30 KB picker + ~83 KB data, gzip): not in the app's first load. */
function load() {
  return import("./emojiMart");
}

/** A token's color as "r, g, b", the form Emoji Mart's variables take (read from the page). */
function rgb(token: string, probe: HTMLElement): string {
  probe.style.color = `var(${token})`;
  const parts = getComputedStyle(probe).color.match(/\d+(\.\d+)?/g) ?? [];
  return parts.slice(0, 3).join(", ");
}

/** Our tokens on Emoji Mart, which draws in a shadow root that our CSS cannot reach. */
function themeOf(host: HTMLElement): Record<string, string> {
  const probe = document.createElement("span");
  host.append(probe);
  const root = getComputedStyle(document.documentElement);
  const theme = {
    "--rgb-accent": rgb("--color-accent", probe),
    "--rgb-background": rgb("--color-surface", probe),
    "--rgb-color": rgb("--color-text", probe),
    "--color-border": root.getPropertyValue("--color-border").trim(),
    "--font-family": root.getPropertyValue("--font-sans").trim(),
    "--border-radius": root.getPropertyValue("--radius-lg").trim(),
    "--shadow": "none",
  };
  probe.remove();
  return theme;
}

/** Dark when the page says so (forced) or the phone does (system). */
function dark(): boolean {
  const forced = document.documentElement.dataset.theme;
  if (forced) return forced === "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

/**
 * Any emoji, with search, categories and skin tones (Emoji Mart, native emoji). Fills its
 * container, so put it in a `Sheet`. Loads on first use with a skeleton; a failed load shows a
 * banner with "Try again".
 */
export function EmojiPicker({
  onPick,
  texts,
  errorText,
  retryLabel,
}: {
  /** The emoji as text, skin tone included. */
  onPick: (emoji: string) => void;
  texts: EmojiPickerTexts;
  errorText: string;
  retryLabel: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [settled, setSettled] = useState<{ attempt: number; ok: boolean } | null>(null);
  const state = settled?.attempt !== attempt ? "loading" : settled.ok ? "ready" : "error";
  const pick = useRef(onPick);

  useEffect(() => {
    pick.current = onPick;
  }, [onPick]);

  useEffect(() => {
    let gone = false;
    load().then(
      ({ Picker, data }) => {
        const container = host.current;
        if (gone || !container) return;
        const picker = new Picker({
          data,
          i18n: texts,
          set: "native",
          theme: dark() ? "dark" : "light",
          previewPosition: "none",
          skinTonePosition: "search",
          navPosition: "top",
          maxFrequentRows: 1,
          emojiButtonSize: 44,
          emojiSize: 28,
          dynamicWidth: true,
          onEmojiSelect: (emoji: { native: string }) => pick.current(emoji.native),
        }) as unknown as HTMLElement;
        for (const [name, value] of Object.entries(themeOf(container))) {
          picker.style.setProperty(name, value);
        }
        container.replaceChildren(picker);
        setSettled({ attempt, ok: true });
      },
      () => !gone && setSettled({ attempt, ok: false }),
    );
    return () => {
      gone = true;
    };
  }, [texts, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return (
    <div className={styles.picker}>
      {state === "loading" && <Skeleton lines={6} />}
      <Banner
        open={state === "error"}
        tone="danger"
        title={errorText}
        actions={
          <Button variant="secondary" onClick={retry}>
            {retryLabel}
          </Button>
        }
      />
      <div ref={host} className={styles.host} hidden={state !== "ready"} />
    </div>
  );
}
