import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { bogdan, meAs } from "@/test/fixtures";
import { ok, renderRoutes } from "@/test/render";

import { SpinsCard, SpinsRoute } from ".";
import type { Spin } from "./api";

const punishments = [
  { position: 1, text: "20 burpees", proof_required: true },
  { position: 2, text: "No phone after 21:00", proof_required: false },
  { position: 3, text: "Cold shower, 2 minutes", proof_required: true },
];

const pending: Spin = {
  id: "s1",
  challenge: { id: "swim", title: "Swim", icon: "water", measure: "check", unit: "" },
  need_kind: "count",
  window_first: "2026-11-02",
  window_last: "2026-11-08",
  need: 3,
  done: 1,
  punishments,
  punishment: null,
  state: "pending",
  drawn_at: null,
  serve_by: null,
  late: false,
  proofs: [],
};

const drawn = (position: number, overrides: Partial<Spin> = {}): Spin => ({
  ...pending,
  punishment: punishments[position - 1] ?? null,
  state: "spun",
  drawn_at: "2026-11-09T08:00:00Z",
  serve_by: "2026-11-16",
  ...overrides,
});

function mockSpins(spins: Spin[]) {
  return vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(meAs(bogdan));
    const toSpin = spins.filter((s) => s.state === "pending").length;
    return ok({ to_spin: toSpin, to_serve: spins.length - toSpin, spins });
  }) as never);
}

beforeAll(() => {
  // Reduced motion: the dial stops at once, so the tests need not wait 3.6 s.
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (query: string) => ({
      matches: query.includes("reduce"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
    }),
  });
});
afterEach(() => vi.restoreAllMocks());

describe("the spins card on Today", () => {
  it("says what is owed and opens the spins", async () => {
    mockSpins([pending, drawn(1, { id: "s2", late: true })]);
    renderRoutes([
      { path: "/", element: <SpinsCard /> },
      { path: "/spins", element: <p>Spins page</p> },
    ]);

    expect(await screen.findByRole("heading", { name: "1 spin · 1 to serve" })).toBeVisible();
    expect(screen.getByText("1 punishment is late")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: /1 spin · 1 to serve/ }));
    expect(await screen.findByText("Spins page")).toBeInTheDocument();
  });

  it("is not there when nothing is owed", async () => {
    const get = mockSpins([]);
    renderRoutes([{ path: "/", element: <SpinsCard /> }]);
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(screen.queryByRole("heading")).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
  });
});

describe("the spins page", () => {
  it("draws on the server, then asks for Done when no proof is needed", async () => {
    mockSpins([pending]);
    const post = vi
      .spyOn(api, "POST")
      .mockImplementation(((path: string) =>
        ok(path.endsWith("/draw") ? drawn(2) : drawn(2, { state: "served" }))) as never);
    renderRoutes([{ path: "/", element: <SpinsRoute /> }]);

    expect(await screen.findByText("November 2 – November 8: 1 of 3")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "A dial with 3 punishments" })).toBeInTheDocument();
    expect(screen.getByText("Each one is 1 in 3, drawn before the dial turns.")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Spin" }));

    expect(post).toHaveBeenCalledWith("/api/v1/spins/{spin_id}/draw", {
      params: { path: { spin_id: "s1" } },
    });
    const result = await screen.findByRole("status");
    expect(within(result).getByRole("heading", { name: "No phone after 21:00" })).toBeVisible();
    expect(within(result).getByText("Serve by Monday, November 16")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(post).toHaveBeenCalledWith("/api/v1/spins/{spin_id}/done", {
      params: { path: { spin_id: "s1" } },
    });
    expect(await screen.findByText("Served")).toBeInTheDocument();
  });

  it("asks for proof when the punishment needs it, and says when it is late", async () => {
    mockSpins([drawn(3, { late: true })]);
    renderRoutes([{ path: "/", element: <SpinsRoute /> }]);

    expect(
      await screen.findByRole("img", {
        name: "A dial with 3 punishments: 3 was drawn, Cold shower, 2 minutes",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Late")).toBeInTheDocument();
    expect(screen.getByText("Was due Monday, November 16")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add a photo or video" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Done" })).toBeNull();
  });

  it("says when there is nothing to spin", async () => {
    mockSpins([]);
    renderRoutes([{ path: "/", element: <SpinsRoute /> }]);
    expect(await screen.findByRole("heading", { name: "Nothing to spin" })).toBeVisible();
  });
});
