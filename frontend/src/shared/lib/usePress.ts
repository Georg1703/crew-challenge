import { useCallback, useEffect, useRef, type MouseEvent, type PointerEvent } from "react";

import { tap } from "./haptics";

const MOVE_PX = 10; // a finger that moves this far is scrolling, not pressing

export interface PressHandlers {
  onClick: (event: MouseEvent) => void;
  onContextMenu: (event: MouseEvent) => void;
  onPointerDown: (event: PointerEvent) => void;
  onPointerMove: (event: PointerEvent) => void;
  onPointerUp: () => void;
  onPointerCancel: () => void;
  onPointerLeave: () => void;
}

/**
 * Tap and press-and-hold on one control. Spread the handlers on a button: a tap (or Enter and
 * Space, which click it) calls `onPress`; holding still for `delay` ms calls `onLongPress` with a
 * haptic tick, and the click that follows is ignored. The context menu (right click, the menu
 * key, Shift+F10, Android's own long press) also calls `onLongPress`, so it works without a
 * finger. Moving the finger cancels, so scrolling over a control never triggers it.
 */
export function usePress({
  onPress,
  onLongPress,
  delay = 500,
}: {
  onPress: () => void;
  onLongPress: () => void;
  delay?: number;
}): PressHandlers {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const start = useRef<{ x: number; y: number } | null>(null);
  const held = useRef(false);

  const cancel = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    start.current = null;
  }, []);

  useEffect(() => cancel, [cancel]);

  const long = useCallback(() => {
    held.current = true;
    tap();
    onLongPress();
  }, [onLongPress]);

  return {
    onPointerDown: (event) => {
      held.current = false;
      start.current = { x: event.clientX, y: event.clientY };
      timer.current = setTimeout(() => {
        timer.current = null;
        long();
      }, delay);
    },
    onPointerMove: (event) => {
      const from = start.current;
      if (from && Math.hypot(event.clientX - from.x, event.clientY - from.y) > MOVE_PX) cancel();
    },
    onPointerUp: cancel,
    onPointerCancel: cancel,
    onPointerLeave: cancel,
    onContextMenu: (event) => {
      event.preventDefault();
      if (held.current) return; // the timer already fired for this press
      const pressing = start.current !== null; // a finger is down: ignore the click after it
      cancel();
      long();
      held.current = pressing;
    },
    onClick: (event) => {
      if (held.current) {
        held.current = false;
        event.preventDefault();
        return;
      }
      onPress();
    },
  };
}

/**
 * Press and hold anywhere on an element we do not render (the card around a control): a finger
 * held still for `delay` ms calls `onLongPress` with a haptic tick, and the click after it and the
 * phone's own long-press menu are eaten. Presses that start inside `skip` (the control itself)
 * are left alone, and so is a mouse (it has the control's button). Returns the clean-up.
 */
export function holdOn(
  element: HTMLElement,
  onLongPress: () => void,
  { skip, delay = 500 }: { skip?: Element | null; delay?: number } = {},
): () => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let start: { x: number; y: number } | null = null;
  let held = false;
  const cancel = () => {
    clearTimeout(timer);
    timer = undefined;
    start = null;
  };
  const fire = () => {
    cancel();
    held = true;
    tap();
    onLongPress();
  };
  const down = (event: globalThis.PointerEvent) => {
    held = false;
    if (event.pointerType === "mouse" || skip?.contains(event.target as Node)) return;
    start = { x: event.clientX, y: event.clientY };
    timer = setTimeout(fire, delay);
  };
  const move = (event: globalThis.PointerEvent) => {
    if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > MOVE_PX) cancel();
  };
  const menu = (event: Event) => {
    if (!start && !held) return; // a right click: the browser's own menu
    event.preventDefault();
    if (!held) fire(); // Android's long press came first
  };
  const click = (event: Event) => {
    if (!held) return;
    held = false;
    event.preventDefault();
    event.stopPropagation(); // a proof tile under the finger does not open
  };
  element.addEventListener("pointerdown", down);
  element.addEventListener("pointermove", move);
  element.addEventListener("pointerup", cancel);
  element.addEventListener("pointercancel", cancel);
  element.addEventListener("contextmenu", menu);
  element.addEventListener("click", click, true);
  return () => {
    cancel();
    element.removeEventListener("pointerdown", down);
    element.removeEventListener("pointermove", move);
    element.removeEventListener("pointerup", cancel);
    element.removeEventListener("pointercancel", cancel);
    element.removeEventListener("contextmenu", menu);
    element.removeEventListener("click", click, true);
  };
}
