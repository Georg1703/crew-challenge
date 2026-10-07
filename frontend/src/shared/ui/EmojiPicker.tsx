import { useCallback, useEffect, useRef, useState } from "react";

import { Banner } from "./Banner";
import { Button } from "./Button";
import styles from "./EmojiPicker.module.css";
import { useSheetSettled } from "./Sheet";
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

/** Start loading the picker early (when a quick row opens), so "+" opens at once. */
export function preloadEmojiPicker(): void {
  void load().catch(() => undefined); // a failure shows when the picker opens
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

/**
 * Emoji Mart's sticky category titles blur what scrolls under them (`backdrop-filter`): costly on
 * Android phones while the list moves. A solid background instead (its shadow root is open).
 */
function solidTitles(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent =
    "#root .sticky{backdrop-filter:none;background-color:rgb(var(--em-rgb-background))}";
  return style;
}

/** Dark when the page says so (forced) or the phone does (system). */
function dark(): boolean {
  const forced = document.documentElement.dataset.theme;
  if (forced) return forced === "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

/**
 * Any emoji, with search, categories and skin tones (Emoji Mart, native emoji). Fills its
 * container, so put it in a `Sheet`; it is built once the sheet has slid in. Loads on first use
 * with a skeleton; a failed load shows a banner with "Try again".
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
  const frame = useRef<HTMLDivElement>(null);
  const host = useRef<HTMLDivElement>(null);
  const slidIn = useSheetSettled();
  const [attempt, setAttempt] = useState(0);
  const [settled, setSettled] = useState<{ attempt: number; ok: boolean } | null>(null);
  const state = settled?.attempt !== attempt ? "loading" : settled.ok ? "ready" : "error";
  const pick = useRef(onPick);

  useEffect(() => {
    pick.current = onPick;
  }, [onPick]);

  useEffect(() => {
    if (!slidIn) return;
    let gone = false;
    load().then(
      ({ Picker, data }) => {
        const container = host.current;
        if (gone || !container || !frame.current) return;
        // The grid is sized here, once: Emoji Mart's `dynamicWidth` builds it twice on every open
        // (its ResizeObserver always rebuilds after the first build). Room = our width less its
        // left padding (12) and scrollbar gutter (16); buttons grow from 44 px to fill the row.
        // ponytail: a phone rotated while the sheet is open keeps the old grid until it reopens.
        const room = frame.current.clientWidth - 28;
        const perLine = Math.max(1, Math.floor(room / 44));
        const picker = new Picker({
          data,
          i18n: texts,
          set: "native",
          theme: dark() ? "dark" : "light",
          previewPosition: "none",
          skinTonePosition: "search",
          navPosition: "top",
          maxFrequentRows: 1,
          perLine,
          emojiButtonSize: Math.max(44, Math.floor(room / perLine)),
          emojiSize: 28,
          onEmojiSelect: (emoji: { native: string }) => pick.current(emoji.native),
        }) as unknown as HTMLElement;
        for (const [name, value] of Object.entries(themeOf(container))) {
          picker.style.setProperty(name, value);
        }
        picker.shadowRoot?.append(solidTitles());
        container.replaceChildren(picker);
        setSettled({ attempt, ok: true });
      },
      () => !gone && setSettled({ attempt, ok: false }),
    );
    return () => {
      gone = true;
    };
  }, [texts, attempt, slidIn]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return (
    <div ref={frame} className={styles.picker}>
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
