/**
 * Translations. Romanian is the default; English is the second language.
 * Add every key to BOTH ro.json and en.json (a test checks they match).
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import ro from "./ro.json";

export const LANGUAGES = ["ro", "en"] as const;
export type Language = (typeof LANGUAGES)[number];

const STORAGE_KEY = "language";

function initialLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "ro" || stored === "en") return stored;
  } catch {
    // Storage can be unavailable (private mode); fall through.
  }
  return navigator.language.toLowerCase().startsWith("en") ? "en" : "ro";
}

void i18n.use(initReactI18next).init({
  resources: { ro: { translation: ro }, en: { translation: en } },
  lng: initialLanguage(),
  fallbackLng: "ro",
  interpolation: { escapeValue: false }, // React escapes already
  returnNull: false,
});

/** Switch the UI language and remember it on this device. */
export function setLanguage(language: Language): void {
  void i18n.changeLanguage(language);
  document.documentElement.lang = language;
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Not critical.
  }
}

document.documentElement.lang = i18n.language;

export { i18n };
