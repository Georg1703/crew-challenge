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
