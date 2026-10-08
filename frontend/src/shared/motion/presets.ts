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

/**
 * The Wheel of Doom's dial turning to the drawn punishment: a few full turns that slow down to a
 * stop, long enough to feel like a spin (3.6 s). Reduced motion: it is there at once.
 */
export const dialTurn = { duration: 3.6, ease: [0.12, 0.7, 0.12, 1] } satisfies Transition;

/** Delay between children of a staggered list, in seconds. */
export const staggerStep = 0.06;

/**
 * A picked reaction flying into place: from the finger it grows big over the card's middle, wiggles
 * left and right, then shrinks into its chip. Fast: about 0.6 s in all.
 */
export const emojiFlight = {
  /** To the middle of the card, growing. */
  out: { duration: 0.18, ease: [0.2, 0.8, 0.2, 1] },
  /** The wiggle in the middle. */
  hold: { duration: 0.24, ease: "easeInOut" },
  /** Into the chip, shrinking. */
  back: { duration: 0.2, ease: [0.4, 0, 0.6, 1] },
  /** Its size as it leaves the finger, over the card, and as it lands (x the flying emoji). */
  start: 0.65,
  peak: 3.2,
  land: 0.5,
  /** The wiggle: degrees left and right while it is big (it leans left on the way out). */
  wiggle: [-12, 12, -8, 0],
} satisfies {
  out: Transition;
  hold: Transition;
  back: Transition;
  start: number;
  peak: number;
  land: number;
  wiggle: number[];
};

/** Scale applied while a pressable element is held down. */
export const pressScale = 0.96;

/** Press-and-hold to confirm (check in): how long to hold, and the fill that shows it. */
export const holdToConfirm = {
  ms: 600,
  fill: { duration: 0.6, ease: "linear" },
  release: { duration: 0.15, ease: "easeOut" },
} satisfies { ms: number; fill: Transition; release: Transition };
