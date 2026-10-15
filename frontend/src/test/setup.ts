import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { i18n } from "@/i18n";

// Tests read English text; the app defaults to Romanian.
void i18n.changeLanguage("en");

// jsdom lays nothing out: what the app watches never comes into view, and scrolling does nothing.
class NothingInView {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}
globalThis.IntersectionObserver ??= NothingInView as unknown as typeof IntersectionObserver;
Element.prototype.scrollIntoView ??= () => {};
window.scrollTo = () => {};
// jsdom has no canvas: confetti is a no-op in tests.
vi.mock("canvas-confetti", () => ({ default: vi.fn(() => Promise.resolve()) }));

afterEach(() => {
  cleanup();
  document.cookie = "crew_csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});
