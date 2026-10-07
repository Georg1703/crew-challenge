import { describe, expect, it } from "vitest";

import {
  addDays,
  dayOfMonth,
  daysBetween,
  mondayOf,
  monthStart,
  periodEnd,
  weekday,
} from "./dates";

describe("crew-local dates", () => {
  it("adds days across months, years and the night the clocks go back", () => {
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-10-26", -2)).toBe("2026-10-24"); // over 25 October
    expect(daysBetween("2026-10-24", "2026-10-26")).toBe(2);
  });

  it("knows weekdays, Mondays and days of the month", () => {
    expect(weekday("2026-11-02")).toBe(0); // a Monday
    expect(weekday("2026-11-01")).toBe(6);
    expect(mondayOf("2026-11-01")).toBe("2026-10-26");
    expect(mondayOf("2026-11-02")).toBe("2026-11-02");
    expect(dayOfMonth("2026-11-09")).toBe(9);
  });

  it("moves by months and ends a period", () => {
    expect(monthStart("2026-11-20")).toBe("2026-11-01");
    expect(monthStart("2026-11-20", 2)).toBe("2027-01-01");
    expect(monthStart("2026-01-20", -1)).toBe("2025-12-01");
    expect(periodEnd("month", "2027-02-01", 1)).toBe("2027-02-28");
    expect(periodEnd("month", "2026-11-01", 3)).toBe("2027-01-31");
    expect(periodEnd("week", "2026-11-02", 4)).toBe("2026-11-29");
    expect(periodEnd("day", "2026-10-10", 21)).toBe("2026-10-30");
  });
});
