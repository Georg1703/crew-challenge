/**
 * Confetti for a check-in: a burst from the button on every post, a big one when the day lands
 * done. The library loads on the first burst, never with the app shell. Nothing when the user
 * prefers reduced motion (the library checks). Feedback only: a failure to draw is swallowed.
 */
export async function burst(origin: Element | null = null, { big = false } = {}): Promise<void> {
  try {
    const { default: confetti } = await import("canvas-confetti");
    const rect = origin?.getBoundingClientRect();
    const from = rect
      ? {
          x: (rect.left + rect.width / 2) / window.innerWidth,
          y: (rect.top + rect.height / 2) / window.innerHeight,
        }
      : { y: 0.6 };
    void confetti({
      particleCount: big ? 300 : 80,
      spread: big ? 120 : 60,
      startVelocity: big ? 50 : 30,
      ticks: big ? 250 : 120,
      scalar: big ? 1.2 : 1,
      disableForReducedMotion: true,
      origin: from,
    });
  } catch {
    // ponytail: no canvas (old WebView, jsdom) means no confetti, not an error
  }
}
