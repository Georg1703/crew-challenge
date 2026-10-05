import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ana, bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { ChallengeRoute, ChallengesRoute, ProposeRoute, TodayChallenges } from ".";
import type { Challenge, ChallengeDetail, Pool } from "./api";
import { monthOptions } from "./months";

const person = (member: typeof ana) => ({
  id: member.id,
  display_name: member.display_name,
  avatar_seed: member.avatar_seed,
});

const pushUps: Challenge = {
  id: "c1",
  title: "50 push-ups",
  rules: "",
  icon: "dumbbell",
  measure: "quantity",
  unit: "push-ups",
  frequency: "daily",
  weekdays: [],
  times: null,
  target_scope: "per_check_in",
  target_value: 50,
  proof_kind: "video",
  proof_required: true,
  state: "proposed",
  phase: null,
  period_kind: null,
  period_start: null,
  start_date: null,
  end_date: null,
  chosen_by: null,
  chosen_at: null,
  created_by: person(bogdan),
  created_at: "2026-10-02T09:00:00Z",
  revision: 1,
  vote_count: 1,
  voters: [person(bogdan)],
  my_vote: false,
  mine: false,
};

const reading: Challenge = { ...pushUps, id: "c2", title: "Read", vote_count: 3, voters: [] };

const pool: Pool = { proposals: [pushUps], size: 1, limit: 50 };

const scheduled = (overrides: Partial<Challenge> = {}): Challenge => ({
  ...pushUps,
  state: "chosen",
  phase: "upcoming",
  period_kind: "month",
  period_start: "2026-11-01",
  start_date: "2026-11-01",
  end_date: "2026-11-30",
  chosen_by: person(ana),
  chosen_at: "2026-10-05T09:00:00Z",
  ...overrides,
});

const detail = (overrides: Partial<ChallengeDetail> = {}): ChallengeDetail => ({
  ...pushUps,
  participants: [],
  taking_part: false,
  ...overrides,
});

type Value<T> = T | (() => T);
const value = <T,>(v: Value<T>) => (typeof v === "function" ? (v as () => T)() : v);

/** Answers every GET the challenge screens make; pass functions for data a test changes. */
function mockGets(
  member = ana,
  {
    proposals = pool as Value<Pool>,
    chosen = [] as Value<Challenge[]>,
    one = detail() as Value<ChallengeDetail>,
  } = {},
) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(meAs(member));
    if (path === "/api/v1/proposals") return ok(value(proposals));
    if (path === "/api/v1/challenges") return ok(value(chosen));
    if (path === "/api/v1/challenges/{challenge_id}") return ok(value(one));
    return fail(404, { code: "not_found" });
  }) as never);
}

const routes = [
  { path: "/challenges", element: <ChallengesRoute /> },
  { path: "/challenges/new", element: <ProposeRoute /> },
  { path: "/challenges/:id", element: <ChallengeRoute /> },
];

describe("month options", () => {
  it("offers the rest of this month and the next three", () => {
    expect(monthOptions("2026-10-05")).toEqual([
      { periodStart: "2026-10-01", startsOn: "2026-10-06" },
      { periodStart: "2026-11-01", startsOn: "2026-11-01" },
      { periodStart: "2026-12-01", startsOn: "2026-12-01" },
      { periodStart: "2027-01-01", startsOn: "2027-01-01" },
    ]);
  });

  it("leaves out this month on its last day", () => {
    expect(monthOptions("2026-10-31").map((o) => o.periodStart)).toEqual([
      "2026-11-01",
      "2026-12-01",
      "2027-01-01",
    ]);
  });
});

describe("challenges list", () => {
  it("shows the pool with who proposed, the votes and how full it is", async () => {
    mockGets(bogdan);
    renderRoutes(routes, { at: "/challenges" });

    expect(await screen.findByRole("heading", { name: "Proposals" })).toBeInTheDocument();
    expect(screen.getByText("1 of 50")).toBeInTheDocument();
    expect(screen.getByText("50 push-ups")).toBeInTheDocument();
    expect(screen.getByText(/Proposed by Bogdan/)).toBeInTheDocument();
    expect(screen.getByText("Votes: 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Choose" })).not.toBeInTheDocument();
  });

  it("says when the pool is empty", async () => {
    mockGets(bogdan, { proposals: { proposals: [], size: 0, limit: 50 } });
    renderRoutes(routes, { at: "/challenges" });

    expect(
      await screen.findByText("No proposals yet. Propose what the crew could do next."),
    ).toBeInTheDocument();
  });

  it("stops new proposals when the pool is full", async () => {
    mockGets(bogdan, { proposals: { ...pool, size: 1, limit: 1 } });
    renderRoutes(routes, { at: "/challenges" });

    expect(await screen.findByText(/The list is full \(1 proposals\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Propose a challenge" })).toBeDisabled();
  });

  it("groups upcoming challenges by month", async () => {
    mockGets(bogdan, {
      chosen: [
        scheduled(),
        scheduled({ id: "c3", title: "Read" }),
        scheduled({
          id: "c4",
          title: "Swim",
          period_start: "2026-12-01",
          start_date: "2026-12-01",
          end_date: "2026-12-31",
        }),
      ],
    });
    renderRoutes(routes, { at: "/challenges" });

    expect(await screen.findByRole("heading", { name: "November 2026" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "December 2026" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "November 2026" }).children).toHaveLength(2);
  });

  it("votes for a proposal and shows the vote at once", async () => {
    let current = pool;
    mockGets(bogdan, { proposals: () => current });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => {
      const voted = { ...pushUps, my_vote: true, vote_count: 2 };
      current = { ...pool, proposals: [voted] };
      return ok(voted);
    }) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Vote" }));

    expect(await screen.findByRole("button", { name: "Voted" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("Votes: 2")).toBeInTheDocument();
    expect(put).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/vote", {
      params: { path: { challenge_id: "c1" } },
    });
  });

  it("lets an admin sort by votes", async () => {
    mockGets(ana, { proposals: { proposals: [pushUps, reading], size: 2, limit: 50 } });
    renderRoutes(routes, { at: "/challenges" });

    await screen.findByText("50 push-ups");
    const titles = () => screen.getAllByRole("link").map((link) => link.textContent);
    expect(titles()[0]).toContain("50 push-ups");
    await userEvent.click(screen.getByRole("radio", { name: "Most votes" }));
    expect(titles()[0]).toContain("Read");
  });

  it("lets an admin choose the month for a proposal", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-10-05T09:00:00Z") });
    mockGets(ana);
    const put = vi
      .spyOn(api, "PUT")
      .mockImplementation((() => ok(detail({ ...scheduled() }))) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Choose" }));
    const sheet = await screen.findByRole("dialog");
    expect(within(sheet).getByText("When does “50 push-ups” run?")).toBeVisible();
    expect(within(sheet).getByRole("radio", { name: /October 2026/ })).toBeInTheDocument();
    expect(within(sheet).getByRole("radio", { name: /November 2026/ })).toBeChecked();
    await userEvent.click(within(sheet).getByRole("radio", { name: /December 2026/ }));
    await userEvent.click(within(sheet).getByRole("button", { name: "Choose for December" }));

    expect(await screen.findByText("Scheduled for December")).toBeInTheDocument();
    expect(put).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/schedule", {
      params: { path: { challenge_id: "c1" } },
      body: { period_kind: "month", period_start: "2026-12-01" },
    });
    vi.useRealTimers();
  });
});

describe("proposing", () => {
  it("asks for a name before moving on", async () => {
    mockGets(bogdan);
    renderRoutes(routes, { at: "/challenges/new" });

    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));

    expect(await screen.findByText("Give the challenge a name.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What do you propose?" })).toBeInTheDocument();
  });

  it("walks through the steps and publishes the proposal", async () => {
    mockGets(bogdan);
    const post = vi.spyOn(api, "POST").mockImplementation((() => ok(detail(), 201)) as never);
    const { router } = renderRoutes(routes, { at: "/challenges/new" });

    await userEvent.type(await screen.findByLabelText("Name of the challenge"), "Read");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "How often?" });
    await userEvent.click(screen.getByRole("radio", { name: /A few times a week/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "What do you record?" });
    await userEvent.click(screen.getByRole("radio", { name: /A number/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Write the unit, for example km.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Unit"), "pages");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "What proof?" });
    await userEvent.click(screen.getByRole("radio", { name: /Quick, works for almost anything/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("heading", { name: "Check it" });
    expect(screen.getByText("3 times a week")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Publish the proposal" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/challenges/c1"));
    expect(post).toHaveBeenCalledWith("/api/v1/challenges", {
      body: {
        title: "Read",
        rules: "",
        icon: "star",
        measure: "quantity",
        unit: "pages",
        frequency: "times_per_week",
        weekdays: [],
        times: 3,
        target_scope: "none",
        target_value: null,
        proof_kind: "photo",
        proof_required: false,
      },
    });
  });

  it("explains a full pool", async () => {
    mockGets(bogdan);
    vi.spyOn(api, "POST").mockImplementation((() => fail(409, { code: "pool_full" })) as never);
    renderRoutes(routes, { at: "/challenges/new" });

    await userEvent.type(await screen.findByLabelText("Name of the challenge"), "Read");
    for (let step = 0; step < 4; step += 1) {
      await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    }
    await userEvent.click(await screen.findByRole("button", { name: "Publish the proposal" }));

    expect(await screen.findByText(/The list of proposals is full/)).toBeInTheDocument();
  });
});

describe("one challenge", () => {
  it("lets the creator vote, edit or withdraw a proposal", async () => {
    mockGets(bogdan, { one: detail({ mine: true }) });
    renderRoutes(routes, { at: "/challenges/c1" });

    expect(await screen.findByRole("heading", { name: "50 push-ups" })).toBeInTheDocument();
    expect(screen.getByText("At least 50 push-ups each check-in")).toBeInTheDocument();
    expect(screen.getByText("Video, required")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Vote" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Edit the proposal" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Withdraw the proposal" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Choose a month" })).not.toBeInTheDocument();
  });

  it("lets an admin move a scheduled challenge or put it back in the pool", async () => {
    const chosen = detail({ ...scheduled(), taking_part: true });
    let one = chosen;
    mockGets(ana, { one: () => one });
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => {
      one = detail();
      return ok(one);
    }) as never);
    renderRoutes(routes, { at: "/challenges/c1" });

    expect(await screen.findByText("November 2026")).toBeInTheDocument();
    expect(screen.getByText(/Chosen by Ana/)).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Move to another month" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back to proposals" }));

    expect(await screen.findByText("Back in the proposals")).toBeInTheDocument();
    expect(del).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/schedule", {
      params: { path: { challenge_id: "c1" } },
    });
    expect(await screen.findByRole("button", { name: "Vote" })).toBeInTheDocument();
  });

  it("lets a member opt out of a scheduled challenge before it starts", async () => {
    const chosen = detail({
      ...scheduled(),
      taking_part: true,
      participants: [{ member: person(bogdan), joined_on: "2026-11-01", ended_on: null }],
    });
    const optedOut = { ...chosen, taking_part: false, participants: [] };
    let one = chosen;
    mockGets(bogdan, { one: () => one });
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => {
      one = optedOut;
      return ok(optedOut);
    }) as never);
    renderRoutes(routes, { at: "/challenges/c1" });

    await userEvent.click(await screen.findByRole("button", { name: "I'm not taking part" }));

    expect(await screen.findByRole("button", { name: "I'm taking part" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to proposals" })).not.toBeInTheDocument();
    expect(del).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/participation", {
      params: { path: { challenge_id: "c1" } },
    });
  });
});

describe("today", () => {
  const today = (member: typeof ana, now: string, chosen: Challenge[] = []) => {
    mockGets(member, { chosen });
    renderRoutes([
      {
        path: "/",
        element: (
          <TodayChallenges
            isAdmin={member.role === "admin"}
            timeZone="Europe/Chisinau"
            now={new Date(now)}
          />
        ),
      },
    ]);
  };

  it("invites people to vote on the proposals", async () => {
    today(bogdan, "2026-10-26T09:00:00Z");
    expect(
      await screen.findByRole("heading", { name: "Proposals for the next challenges" }),
    ).toBeInTheDocument();
    expect(screen.getByText("One proposal. Vote if you like it.")).toBeInTheDocument();
  });

  it("reminds admins from the 25th when next month has no challenge", async () => {
    today(ana, "2026-10-26T09:00:00Z");
    expect(
      await screen.findByRole("heading", { name: "No challenge for November yet" }),
    ).toBeInTheDocument();
  });

  it("does not remind admins when next month has a challenge", async () => {
    today(ana, "2026-10-26T09:00:00Z", [scheduled()]);
    expect(
      await screen.findByRole("heading", { name: "Proposals for the next challenges" }),
    ).toBeInTheDocument();
  });
});
