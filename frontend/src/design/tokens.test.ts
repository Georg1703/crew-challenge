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

describe("design tokens", () => {
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
