import { afterEach, describe, expect, it } from "vitest";

import { applyTheme, setTheme, storedTheme } from "./theme";

afterEach(() => {
  setTheme("system");
  document.head.innerHTML = "";
});

describe("theme", () => {
  it("follows the phone until someone picks one, and remembers the pick", () => {
    expect(storedTheme()).toBe("system");
    setTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(storedTheme()).toBe("dark");

    setTheme("system");
    expect(document.documentElement.dataset.theme).toBeUndefined();
    expect(storedTheme()).toBe("system");
  });

  it("does not remember a theme only applied (the design page)", () => {
    applyTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(storedTheme()).toBe("system");
  });

  it("gives the browser bar back its own colors when following the phone", () => {
    document.head.innerHTML = '<meta name="theme-color" content="#fbfaf6" />';
    const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    document.documentElement.style.setProperty("--color-bg", "#161a18");
    setTheme("dark");
    expect(meta?.content).toBe("#161a18");
    setTheme("system");
    expect(meta?.content).toBe("#fbfaf6");
    document.documentElement.style.removeProperty("--color-bg");
  });
});
