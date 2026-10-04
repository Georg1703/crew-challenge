import { describe, expect, it } from "vitest";

import en from "./en.json";
import ro from "./ro.json";

function keys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value).flatMap(([key, child]) =>
    keys(child, prefix ? `${prefix}.${key}` : key),
  );
}

describe("translations", () => {
  it("Romanian and English have exactly the same keys", () => {
    expect(keys(en).sort()).toEqual(keys(ro).sort());
  });

  it("every API error code the backend documents has a message", () => {
    const codes = [
      "network_error",
      "server_error",
      "invalid_credentials",
      "throttled",
      "csrf_failed",
      "invite_expired",
      "invite_used",
      "invite_not_found",
      "username_taken",
      "display_name_taken",
      "already_signed_in",
      "already_member",
      "not_crew_member",
      "not_crew_admin",
      "validation_failed",
      "not_authenticated",
      "not_found",
    ];
    for (const code of codes) expect(Object.keys(ro.errors)).toContain(code);
  });
});
