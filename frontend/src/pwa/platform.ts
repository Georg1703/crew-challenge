/** What the device can do for installing the app. Pure functions so they are easy to test. */

export interface Platform {
  /** Running as an installed app (home screen icon), not in a browser tab. */
  standalone: boolean;
  /** iPhone or iPad (iPadOS reports itself as a Mac with touch). */
  ios: boolean;
}

export function detectPlatform(
  nav: Pick<Navigator, "userAgent" | "maxTouchPoints"> & { standalone?: boolean } = navigator,
  matchMedia: (query: string) => { matches: boolean } = (query) =>
    typeof window.matchMedia === "function" ? window.matchMedia(query) : { matches: false },
): Platform {
  const ua = nav.userAgent;
  const ios = /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && nav.maxTouchPoints > 1);
  const standalone = matchMedia("(display-mode: standalone)").matches || nav.standalone === true;
  return { standalone, ios };
}
