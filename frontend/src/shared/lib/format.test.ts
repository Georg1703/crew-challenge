import { describe, expect, it } from "vitest";

import { formatDayLong, formatWhen } from "./format";

const NOW = new Date("2026-11-10T19:00:00Z"); // 21:00 in Chisinau
const when = (iso: string, language = "ro") => formatWhen(iso, language, "Europe/Chisinau", NOW);

describe("formatWhen", () => {
  it("says how long ago within the hour, the time today, yesterday with a time, else the date", () => {
    expect(when("2026-11-10T18:59:40Z")).toBe("acum");
    expect(when("2026-11-10T18:55:00Z")).toBe("acum 5 min.");
    expect(when("2026-11-10T17:30:00Z")).toBe("19:30");
    expect(when("2026-11-09T19:40:00Z")).toBe("ieri 21:40");
    expect(when("2026-11-07T19:40:00Z")).toBe("7 noiembrie la 21:40");
    expect(when("2026-11-10T18:55:00Z", "en")).toBe("5 min. ago");
  });

  it("counts days in the crew's time zone, not the phone's", () => {
    // 22:30 UTC on the 9th is already the 10th in Chisinau: today, not yesterday.
    expect(when("2026-11-09T22:30:00Z")).toBe("00:30");
  });
});

describe("formatDayLong", () => {
  it("names the weekday, capitalized for a heading", () => {
    expect(formatDayLong("2026-10-05", "ro")).toBe("Luni, 5 octombrie");
    expect(formatDayLong("2026-10-05", "en")).toBe("Monday, October 5");
  });
});
