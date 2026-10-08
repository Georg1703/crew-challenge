import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { fail, ok, renderScreen } from "@/test/render";
import { ana, bogdan, crewDetail, meAs } from "@/test/fixtures";

import { CrewRoute, MembersRoute } from ".";

const invite = {
  id: "44444444-4444-4444-4444-444444444444",
  code: "k7p4qdx2mn",
  url: "https://crew.example/join/k7p4qdx2mn",
  expires_at: "2026-11-10T10:00:00Z",
  created_by: { display_name: "Ana", avatar_seed: "a1b2c3d4" },
};

const person = (m: typeof ana) => ({
  id: m.id,
  display_name: m.display_name,
  avatar_seed: m.avatar_seed,
});

function mockGets(me: ReturnType<typeof meAs>, pending: unknown[] = [], crewToday: unknown[] = []) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(me);
    if (path === "/api/v1/today") {
      return ok({
        day: "2026-11-10",
        deadline: "2026-11-10T22:00:00Z",
        challenges: [],
        crew: crewToday,
      });
    }
    if (path === "/api/v1/crew/invites") return ok(pending);
    if (path === "/api/v1/journal") return ok({ results: [], next: null });
    if (path === "/api/v1/proposals") return ok({ proposals: [], size: 0, limit: 50 });
    if (path === "/api/v1/challenges") return ok([]);
    return ok(crewDetail);
  }) as never);
}

describe("crew screen", () => {
  it("starts with everyone's day, you first, and hides an empty pool", async () => {
    mockGets(
      meAs(bogdan),
      [],
      [
        {
          member: person(ana),
          done: 1,
          needed: 2,
          challenges: [
            { challenge_id: "walk", state: "done" },
            { challenge_id: "read", state: "started" },
          ],
        },
      ],
    );
    renderScreen(<CrewRoute />);

    const stories = await screen.findByRole("list", { name: "Today in the crew" });
    const items = within(stories).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual(["BYou-", "AAna1/2"]);
    expect(within(stories).getByRole("link", { name: "Ana: 1 of 2 today" })).toHaveAttribute(
      "href",
      `/crew/members/${ana.id}`,
    );
    expect(within(stories).getByRole("link", { name: "Bogdan: nothing due today" })).toBeTruthy();
    expect(screen.queryByRole("list", { name: "Proposals" })).not.toBeInTheDocument();
  });

  it("lists members in join order and marks you", async () => {
    mockGets(meAs(bogdan));
    renderScreen(<MembersRoute />);

    const list = await screen.findByRole("list", { name: "Crew members" });
    const rows = within(list).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Ana"),
      expect.stringContaining("Bogdan"),
    ]);
    expect(within(rows[0] as HTMLElement).getByText("Admin")).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).getByText("you")).toBeInTheDocument();
  });

  it("shows each member's day on their row", async () => {
    mockGets(
      meAs(bogdan),
      [],
      [
        { member: person(ana), done: 2, needed: 2, challenges: [] },
        { member: person(bogdan), done: 0, needed: 1, challenges: [] },
      ],
    );
    renderScreen(<MembersRoute />);

    const list = await screen.findByRole("list", { name: "Crew members" });
    expect(within(list).getByRole("img", { name: "Ana: 2 of 2 today" })).toBeInTheDocument();
    expect(screen.getByText("Admin · 2 of 2 today")).toBeInTheDocument();
    expect(screen.getByText("Member · 0 of 1 today")).toBeInTheDocument();
  });

  it("only admins see the invite button and the invites they sent", async () => {
    mockGets(meAs(bogdan), [invite]);
    renderScreen(<MembersRoute />);
    await screen.findByRole("list", { name: "Crew members" });
    expect(screen.queryByRole("button", { name: "Invite someone" })).not.toBeInTheDocument();
    expect(screen.queryByText("Invites sent")).not.toBeInTheDocument();
    expect(api.GET).not.toHaveBeenCalledWith("/api/v1/crew/invites");
  });

  it("an admin creates an invite, sees the QR code and copies the link", async () => {
    mockGets(meAs(ana));
    vi.spyOn(api, "POST").mockImplementation((() => ok(invite, 201)) as never);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    renderScreen(<MembersRoute />);
    await userEvent.click(await screen.findByRole("button", { name: "Invite someone" }));

    const sheet = await screen.findByRole("dialog", { name: "Invite someone" });
    expect(await within(sheet).findByLabelText("Invite link")).toHaveValue(invite.url);
    expect(within(sheet).getByRole("img", { name: "Invite QR code" })).toBeInTheDocument();
    expect(within(sheet).getByText("Works for one person, until November 10.")).toBeInTheDocument();
    expect(api.POST).toHaveBeenCalledTimes(1);

    await userEvent.click(within(sheet).getByRole("button", { name: "Copy" }));
    expect(writeText).toHaveBeenCalledWith(invite.url);
    expect(await screen.findByText("Link copied")).toBeInTheDocument();
  });

  it("creates a new link every time the sheet opens", async () => {
    mockGets(meAs(ana), [invite]);
    const post = vi
      .spyOn(api, "POST")
      .mockImplementationOnce((() =>
        ok({ ...invite, url: "https://crew.example/join/first" }, 201)) as never)
      .mockImplementationOnce((() =>
        ok({ ...invite, url: "https://crew.example/join/second" }, 201)) as never);
    renderScreen(<MembersRoute />);

    await userEvent.click(await screen.findByRole("button", { name: "Invite someone" }));
    let sheet = await screen.findByRole("dialog", { name: "Invite someone" });
    expect(await within(sheet).findByLabelText("Invite link")).toHaveValue(
      "https://crew.example/join/first",
    );
    await userEvent.click(within(sheet).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "Invite someone" }));
    sheet = await screen.findByRole("dialog", { name: "Invite someone" });
    expect(await within(sheet).findByLabelText("Invite link")).toHaveValue(
      "https://crew.example/join/second",
    );
    expect(post).toHaveBeenCalledTimes(2);
  });

  it("an admin cancels a pending invite after confirming", async () => {
    mockGets(meAs(ana), [invite]);
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => ok(undefined, 204)) as never);
    renderScreen(<MembersRoute />);

    const pending = await screen.findByRole("list", { name: "Unused invites" });
    expect(within(pending).getByText("Link K7P4QDX2MN")).toBeInTheDocument();
    await userEvent.click(within(pending).getByRole("button", { name: "Cancel" }));
    const confirm = await screen.findByRole("dialog", { name: "Cancel the invite?" });
    // The list refetches after the change; the server now has no pending invites.
    mockGets(meAs(ana), []);
    await userEvent.click(within(confirm).getByRole("button", { name: "Cancel the invite" }));

    expect(del).toHaveBeenCalledWith("/api/v1/crew/invites/{invite_id}", {
      params: { path: { invite_id: invite.id } },
    });
    expect(await screen.findByText("Invite cancelled")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByRole("list", { name: "Unused invites" })).not.toBeInTheDocument(),
    );
  });

  it("puts the invite back when cancelling fails", async () => {
    mockGets(meAs(ana), [invite]);
    vi.spyOn(api, "DELETE").mockImplementation((() => fail(409, { code: "invite_used" })) as never);
    renderScreen(<MembersRoute />);

    const pending = await screen.findByRole("list", { name: "Unused invites" });
    await userEvent.click(within(pending).getByRole("button", { name: "Cancel" }));
    const confirm = await screen.findByRole("dialog", { name: "Cancel the invite?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Cancel the invite" }));

    expect(
      await screen.findByText("The link was already used. Ask for a new one."),
    ).toBeInTheDocument();
    expect(await screen.findByText("Link K7P4QDX2MN")).toBeInTheDocument();
  });
});
