import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ana, bogdan, meAs } from "@/test/fixtures";
import { fail, ok, renderRoutes } from "@/test/render";

import { ChallengeRoute, ChallengesRoute, ProposeRoute } from ".";
import type { ChallengeDetail, Proposal, Round } from "./api";

const person = (member: typeof ana) => ({
  id: member.id,
  display_name: member.display_name,
  avatar_seed: member.avatar_seed,
});

const pushUps: Proposal = {
  id: "c1",
  round_id: "r1",
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
  start_date: null,
  end_date: null,
  created_by: person(bogdan),
  created_at: "2026-10-02T09:00:00Z",
  revision: 1,
  vote_count: 1,
  voters: [person(bogdan)],
  mine: false,
};

const round: Round = {
  id: "r1",
  period_kind: "month",
  period_start: "2026-11-01",
  period_end: "2026-11-30",
  state: "open",
  selection: "admin",
  chosen_id: null,
  chosen_by: null,
  chosen_at: null,
  proposals: [pushUps],
  my_vote: null,
  votes_cast: 1,
};

const detail = (overrides: Partial<ChallengeDetail> = {}): ChallengeDetail => ({
  ...pushUps,
  participants: [],
  taking_part: false,
  ...overrides,
});

/** Answers every GET the challenge screens make; pass functions for data a test changes. */
function mockGets(
  member = ana,
  {
    current = round as Round | (() => Round),
    one = detail() as ChallengeDetail | (() => ChallengeDetail),
  } = {},
) {
  const value = <T,>(v: T | (() => T)) => (typeof v === "function" ? (v as () => T)() : v);
  vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(meAs(member));
    if (path === "/api/v1/rounds/current") return ok(value(current));
    if (path === "/api/v1/challenges") return ok([]);
    if (path === "/api/v1/challenges/{challenge_id}") return ok(value(one));
    return fail(404, { code: "not_found" });
  }) as never);
}

const routes = [
  { path: "/challenges", element: <ChallengesRoute /> },
  { path: "/challenges/new", element: <ProposeRoute /> },
  { path: "/challenges/:id", element: <ChallengeRoute /> },
];

describe("challenges list", () => {
  it("shows next month's proposals with who proposed them and the votes", async () => {
    mockGets(bogdan);
    renderRoutes(routes, { at: "/challenges" });

    expect(await screen.findByRole("heading", { name: "For November" })).toBeInTheDocument();
    expect(screen.getByText("50 push-ups")).toBeInTheDocument();
    expect(screen.getByText(/Proposed by Bogdan/)).toBeInTheDocument();
    expect(screen.getByText("Votes: 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Choose it" })).not.toBeInTheDocument();
  });

  it("says when nobody has proposed anything", async () => {
    mockGets(bogdan, { current: { ...round, proposals: [], votes_cast: 0 } });
    renderRoutes(routes, { at: "/challenges" });

    expect(
      await screen.findByText("Nobody has proposed anything for November yet. Be the first."),
    ).toBeInTheDocument();
  });

  it("votes for a proposal and shows the vote at once", async () => {
    const voted = { ...round, my_vote: "c1" };
    let current = round;
    mockGets(bogdan, { current: () => current });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => {
      current = voted;
      return ok(voted);
    }) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Vote" }));

    expect(await screen.findByRole("button", { name: "Your vote" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(put).toHaveBeenCalledWith("/api/v1/rounds/{round_id}/vote", {
      params: { path: { round_id: "r1" } },
      body: { challenge_id: "c1" },
    });
  });

  it("lets an admin choose a proposal for the month", async () => {
    mockGets(ana);
    const put = vi
      .spyOn(api, "PUT")
      .mockImplementation((() => ok({ ...round, state: "closed", chosen_id: "c1" })) as never);
    renderRoutes(routes, { at: "/challenges" });

    await userEvent.click(await screen.findByRole("button", { name: "Choose it" }));
    const sheet = await screen.findByRole("dialog");
    expect(within(sheet).getByText("Choose “50 push-ups” for November?")).toBeVisible();
    await userEvent.click(within(sheet).getByRole("button", { name: "Choose the challenge" }));

    expect(await screen.findByText("The challenge for November is chosen")).toBeInTheDocument();
    expect(put).toHaveBeenCalledWith("/api/v1/rounds/{round_id}/choice", {
      params: { path: { round_id: "r1" } },
      body: { challenge_id: "c1" },
    });
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
});

describe("one challenge", () => {
  it("lets the creator edit or withdraw a proposal", async () => {
    mockGets(bogdan);
    renderRoutes(routes, { at: "/challenges/c1" });

    expect(await screen.findByRole("heading", { name: "50 push-ups" })).toBeInTheDocument();
    expect(screen.getByText("At least 50 push-ups each check-in")).toBeInTheDocument();
    expect(screen.getByText("Video, required")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Edit the proposal" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Withdraw the proposal" })).toBeInTheDocument();
  });

  it("lets a member opt out of a chosen challenge before it starts", async () => {
    const chosen = detail({
      state: "chosen",
      phase: "upcoming",
      start_date: "2026-11-01",
      end_date: "2026-11-30",
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

    expect(screen.queryByRole("button", { name: "Edit the proposal" })).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "I'm not taking part" }));

    expect(await screen.findByRole("button", { name: "I'm taking part" })).toBeInTheDocument();
    expect(del).toHaveBeenCalledWith("/api/v1/challenges/{challenge_id}/participation", {
      params: { path: { challenge_id: "c1" } },
    });
  });
});
