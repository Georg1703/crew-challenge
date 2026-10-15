import { useEffect, useLayoutEffect, useRef, type RefObject } from "react";

const EDGE = 8; // px kept clear of the screen's edges and of the opener

/**
 * A floating panel by the element that opened it (`ReactionMenu`, `TruncatedText`): placed before
 * it is painted, over the opener (under it when there is no room), its `align` edge on the
 * opener's, inside the screen; closed by Escape, a tap outside it and the opener, and scrolling.
 * Returns the ref for the panel, which is `position: fixed`.
 */
export function usePopover<T extends HTMLElement>({
  open,
  onClose,
  anchor,
  align = "end",
}: {
  open: boolean;
  onClose: () => void;
  /** What opened it: a tap there toggles it instead of closing and reopening. */
  anchor?: RefObject<HTMLElement | null>;
  /** The panel's edge that lines up with the opener's: its right ("end") or its left ("start"). */
  align?: "start" | "end";
}): RefObject<T | null> {
  const panel = useRef<T>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onClose();
    };
    const onDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (panel.current?.contains(target) || anchor?.current?.contains(target)) return;
      onClose();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown, true);
    window.addEventListener("scroll", onClose, { capture: true, passive: true });
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown, true);
      window.removeEventListener("scroll", onClose, { capture: true });
    };
  }, [open, onClose, anchor]);

  useLayoutEffect(() => {
    const element = panel.current;
    const at = anchor?.current?.getBoundingClientRect();
    if (!open || !element || !at) return;
    const width = element.offsetWidth;
    const height = element.offsetHeight;
    const above = at.top - height - EDGE;
    const left = align === "end" ? at.right - width : at.left;
    element.style.left = `${Math.max(EDGE, Math.min(left, window.innerWidth - width - EDGE))}px`;
    element.style.top = `${above >= EDGE ? above : at.bottom + EDGE}px`;
  }, [open, anchor, align]);

  return panel;
}
