/**
 * The only entry point for animation. Features import from "@/shared/motion", never from
 * "motion" directly (ESLint enforces it), so every animation uses the shared presets.
 */
import { useReducedMotion, type Transition } from "motion/react";

import { reducedTransition, springs, type SpringName } from "./presets";

export { AnimatePresence, MotionConfig, motion, useReducedMotion } from "motion/react";
export { pressScale, springs, staggerStep, variants, type SpringName } from "./presets";

/** The named spring, or a short fade when the user prefers reduced motion. */
export function useSpring(name: SpringName): Transition {
  return useReducedMotion() ? reducedTransition : springs[name];
}
