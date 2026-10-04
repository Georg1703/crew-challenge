/**
 * Motion tokens for JavaScript animation. Use these names, never ad-hoc numbers, so the whole
 * app shares one feel. Tune the feel here.
 */
import type { Transition, Variants } from "motion/react";

export const springs = {
  /** Buttons, toggles, small feedback. */
  snappy: { type: "spring", stiffness: 520, damping: 34 },
  /** Celebrations, things popping into view. */
  bouncy: { type: "spring", stiffness: 380, damping: 18 },
  /** Sheets, page transitions, large surfaces. */
  gentle: { type: "spring", stiffness: 180, damping: 26 },
} satisfies Record<string, Transition>;

export type SpringName = keyof typeof springs;

/** Used instead of any spring when the user prefers reduced motion. */
export const reducedTransition: Transition = { duration: 0.12, ease: "easeOut" };

export const variants = {
  popIn: {
    hidden: { opacity: 0, scale: 0.6, y: 8 },
    visible: { opacity: 1, scale: 1, y: 0 },
  },
  fadeUp: {
    hidden: { opacity: 0, y: 12 },
    visible: { opacity: 1, y: 0 },
  },
} satisfies Record<string, Variants>;

/** Delay between children of a staggered list, in seconds. */
export const staggerStep = 0.06;

/** Scale applied while a pressable element is held down. */
export const pressScale = 0.96;
