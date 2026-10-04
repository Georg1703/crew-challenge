import { describe, expect, it } from "vitest";

import { readFileSync } from "node:fs";

// vitest runs from frontend/
const index = readFileSync("src/shared/ui/index.ts", "utf8");
const docs = readFileSync("../docs/design-system.md", "utf8");
const designPage = readFileSync("src/design/DesignRoute.tsx", "utf8");

/** Component names exported by shared/ui (capitalized value exports, not types or helpers). */
function components(): string[] {
  const names = [...index.matchAll(/export \{([^}]+)\}/g)].flatMap((m) =>
    (m[1] ?? "").split(",").map((part) => part.trim()),
  );
  return names.filter((name) => /^[A-Z]/.test(name) && !name.startsWith("type "));
}

// Not rendered on /design: the toast provider wraps the app, and Screen is the page layout every
// route already shows.
const NOT_RENDERED = new Set(["ToastProvider", "Screen"]);

describe("design system docs stay in sync with shared/ui", () => {
  it("finds the components", () => {
    expect(components()).toContain("Button");
  });

  it.each(components())("%s is documented in docs/design-system.md", (name) => {
    if (NOT_RENDERED.has(name)) return;
    expect(docs).toContain(`\`${name}\``);
  });

  it.each(components())("%s is shown on /design", (name) => {
    if (NOT_RENDERED.has(name)) return;
    expect(designPage).toMatch(new RegExp(`<${name}[\\s>]`));
  });
});
