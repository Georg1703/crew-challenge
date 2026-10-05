/**
 * Light or dark: follow the phone ("system") or force one. The choice lives on this device only,
 * like the language. tokens.css re-maps colors under `data-theme` on <html>.
 */
export const THEMES = ["system", "light", "dark"] as const;
export type Theme = (typeof THEMES)[number];

const STORAGE_KEY = "theme";

export function storedTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // Storage can be unavailable (private mode); fall through.
  }
  return "system";
}

/** Apply a theme to the page without remembering it (the /design page uses this). */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  // Say the same in the color-scheme meta, so the browser never darkens a forced light page.
  const scheme = document.querySelector<HTMLMetaElement>('meta[name="color-scheme"]');
  if (scheme) {
    scheme.dataset.content ??= scheme.content;
    scheme.content =
      theme === "light" ? "only light" : theme === "dark" ? "dark" : scheme.dataset.content;
  }
  // The browser bar follows the page: one theme-color per scheme, or the forced background.
  const bg = getComputedStyle(root).getPropertyValue("--color-bg").trim();
  for (const meta of document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')) {
    meta.dataset.content ??= meta.content;
    meta.content = theme === "system" || !bg ? meta.dataset.content : bg;
  }
}

/** Apply a theme and remember it on this device. */
export function setTheme(theme: Theme): void {
  applyTheme(theme);
  try {
    if (theme === "system") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Not critical.
  }
}
