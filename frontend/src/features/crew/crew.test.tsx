import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ok, renderScreen } from "@/test/render";
import { ana, bogdan, crewDetail, meAs } from "@/test/fixtures";

import { CrewRoute } from ".";

function mockGets(me: ReturnType<typeof meAs>) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) =>
    path === "/api/v1/me" ? ok(me) : ok(crewDetail)) as never);
}

describe("crew screen", () => {
  it("lists members in rotation order and marks you and the admin", async () => {
    mockGets(meAs(bogdan));
    renderScreen(<CrewRoute />);

    const rows = await screen.findAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Ana"),
      expect.stringContaining("Bogdan"),
    ]);
    expect(within(rows[0] as HTMLElement).getByText("admin")).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).getByText("you")).toBeInTheDocument();
  });

  it("only admins see the invite button", async () => {
    mockGets(meAs(bogdan));
    renderScreen(<CrewRoute />);
    await screen.findAllByRole("listitem");
    expect(screen.queryByRole("button", { name: "Invite someone" })).not.toBeInTheDocument();
  });

  it("an admin creates an invite link and copies it", async () => {
    mockGets(meAs(ana));
    vi.spyOn(api, "POST").mockImplementation((() =>
      ok(
        { code: "abc", url: "https://crew.example/join/abc", expires_at: "2026-11-10T10:00:00Z" },
        201,
      )) as never);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    renderScreen(<CrewRoute />);
    await userEvent.click(await screen.findByRole("button", { name: "Invite someone" }));

    const sheet = await screen.findByRole("dialog", { name: "Invite someone" });
    expect(await within(sheet).findByText("https://crew.example/join/abc")).toBeInTheDocument();
    // 10:00 UTC is shown in the crew time zone (Chisinau, UTC+2 in November).
    expect(within(sheet).getByText(/Valid until November 10 at 12:00/)).toBeInTheDocument();

    await userEvent.click(within(sheet).getByRole("button", { name: "Copy link" }));
    expect(writeText).toHaveBeenCalledWith("https://crew.example/join/abc");
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });
});
