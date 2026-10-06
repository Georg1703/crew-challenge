import { describe, expect, it } from "vitest";

import { readFileSync } from "node:fs";

import { colorTokens } from "./tokens";

const css = readFileSync("src/styles/tokens.css", "utf8"); // vitest runs from frontend/

function declarations(block: string): Record<string, string> {
  return Object.fromEntries(
    [...block.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2]?.trim() ?? ""]),
  );
}

function blockAfter(selector: string): string {
  const start = css.indexOf(selector);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

/** Resolves `var(--x)` chains in a theme (light = :root, dark = :root plus the dark block). */
function theme(dark: boolean): (name: string) => string {
  const values = {
    ...declarations(blockAfter(":root {")),
    ...(dark ? declarations(blockAfter(':root[data-theme="dark"]')) : {}),
  };
  const resolve = (name: string): string => {
    const value = values[name];
    if (value === undefined) throw new Error(`Unknown token ${name}`);
    const ref = /^var\((--[\w-]+)\)$/.exec(value);
    return ref?.[1] ? resolve(ref[1]) : value;
  };
  return (token) => resolve(`--color-${token}`);
}

function luminance(hex: string): number {
  const full =
    hex.length === 4 ? `#${[...hex.slice(1)].map((c) => c + c).join("")}` : hex.slice(0, 7);
  const channels = [1, 3, 5].map((i) => parseInt(full.slice(i, i + 2), 16) / 255);
  const [r = 0, g = 0, b = 0] = channels.map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

// Text that people must read: WCAG AA (4.5:1) in both themes.
const READABLE: [text: string, background: string][] = [
  ["text", "bg"],
  ["text", "surface"],
  ["text", "surface-sunken"],
  ["text-muted", "bg"],
  ["text-muted", "surface"],
  ["on-accent", "accent"],
  ["on-accent", "accent-pressed"],
  ["accent", "surface"],
  ["success", "success-soft"],
  ["warning", "warning-soft"],
  ["danger", "danger-soft"],
  ["danger", "surface"],
  ["on-avatar", "avatar-1"],
  ["on-avatar", "avatar-2"],
  ["on-avatar", "avatar-3"],
  ["on-avatar", "avatar-4"],
  ["on-avatar", "avatar-5"],
  ["on-media", "media-bg"],
];

describe("design tokens", () => {
  it.each([
    ["light", false],
    ["dark", true],
  ])("text colors reach 4.5:1 on their backgrounds (%s)", (_name, dark) => {
    const color = theme(dark);
    const failing = READABLE.filter(([fg, bg]) => contrast(color(fg), color(bg)) < 4.5).map(
      ([fg, bg]) => `${fg} on ${bg}: ${contrast(color(fg), color(bg)).toFixed(2)}`,
    );
    expect(failing).toEqual([]);
  });

  it("the two dark-theme blocks (system preference and forced) stay identical", () => {
    const system = declarations(blockAfter(':root:not([data-theme="light"])'));
    const forced = declarations(blockAfter(':root[data-theme="dark"]'));
    expect(Object.keys(system).length).toBeGreaterThan(10);
    expect(forced).toEqual(system);
  });

  it("dark mode only re-maps semantic tokens, never primitives", () => {
    const dark = Object.keys(declarations(blockAfter(':root[data-theme="dark"]')));
    expect(dark.filter((name) => name.startsWith("--palette-"))).toEqual([]);
  });

  it("every color shown on /design exists in tokens.css", () => {
    const defined = declarations(blockAfter(":root {"));
    for (const name of colorTokens) expect(defined).toHaveProperty(`--color-${name}`);
  });
});

describe("text fields", () => {
  it("are at least 16px, or iPhone Safari zooms in on focus and the page scrolls sideways", () => {
    const size = declarations(blockAfter(":root {"))["--text-input"] ?? "";
    expect(size).toMatch(/rem$/);
    expect(parseFloat(size)).toBeGreaterThanOrEqual(1);
  });
});
