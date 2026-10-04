import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { RequireAuth } from "@/app/RequireAuth";
import { fail, ok, renderRoutes } from "@/test/render";
import { ana, bogdan, meAs } from "@/test/fixtures";

import { JoinRoute, LoginRoute, WelcomeRoute } from ".";
import { safeNext } from "./next";

const get = () => vi.spyOn(api, "GET");
const post = () => vi.spyOn(api, "POST");

const preview = {
  already_member: false,
  crew_id: null,
  crew_name: "Demo Crew",
  status: "valid",
  expires_at: "2026-11-10T10:00:00Z",
  invited_by: { display_name: "Ana", avatar_seed: "a1" },
  members: [
    { display_name: "Ana", avatar_seed: "a1" },
    { display_name: "Bogdan", avatar_seed: "b2" },
  ],
};

/** GET /me answers `me` (or 401 when null); GET /invites/{code} answers `invite`. */
function mockGets({ me = null, invite = ok(preview) }: { me?: unknown; invite?: unknown }) {
  get().mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return me ? ok(me) : fail(401, { code: "not_authenticated" });
    return invite;
  }) as never);
}

describe("login", () => {
  it("logs in and goes to the page the user wanted", async () => {
    let loggedIn = false;
    get().mockImplementation((() =>
      loggedIn ? ok(meAs(ana)) : fail(401, { code: "not_authenticated" })) as never);
    post().mockImplementation((() => {
      loggedIn = true;
      return ok(undefined, 204);
    }) as never);

    const { router } = renderRoutes(
      [
        { path: "/login", element: <LoginRoute /> },
        { path: "/crew", element: <p>crew page</p> },
      ],
      { at: "/login?next=%2Fcrew" },
    );

    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Username"), "ana");
    await userEvent.type(screen.getByLabelText("Password"), "garden-flame-2026");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("crew page")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/crew");
    expect(api.POST).toHaveBeenCalledWith("/api/v1/auth/login", {
      body: { username: "ana", password: "garden-flame-2026" },
    });
  });

  it("shows wrong credentials in a banner", async () => {
    get().mockImplementation((() => fail(401, { code: "not_authenticated" })) as never);
    post().mockImplementation((() => fail(400, { code: "invalid_credentials" })) as never);
    renderRoutes([{ path: "/login", element: <LoginRoute /> }], { at: "/login" });

    await userEvent.type(await screen.findByLabelText("Username"), "ana");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The username or password doesn't match.",
    );
  });

  it("sends visitors without a session to login, remembering where they were going", async () => {
    get().mockImplementation((() => fail(401, { code: "not_authenticated" })) as never);
    const { router } = renderRoutes(
      [
        { element: <RequireAuth />, children: [{ path: "/me", element: <p>private</p> }] },
        { path: "/login", element: <p>login page</p> },
      ],
      { at: "/me" },
    );
    expect(await screen.findByText("login page")).toBeInTheDocument();
    expect(router.state.location.search).toBe("?next=%2Fme");
  });

  it.each([
    ["/join/abc", "/join/abc"],
    ["/crew?x=1", "/crew?x=1"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
    ["/\t/evil.example", "/"],
    ["/\n/evil.example", "/"],
    ["/%09/evil.example", "/%09/evil.example"],
    ["crew", "/"],
    [null, "/"],
  ])("only follows next=%s inside the app", (next, expected) => {
    expect(safeNext(next)).toBe(expected);
  });
});

describe("join", () => {
  const routes = [
    { path: "/join/:code", element: <JoinRoute /> },
    { path: "/welcome", element: <p>welcome page</p> },
    { path: "/", element: <p>home page</p> },
    { path: "/login", element: <p>login page</p> },
  ];

  it("shows who invites you and who is in the crew", async () => {
    mockGets({});
    renderRoutes(routes, { at: "/join/abc123" });
    expect(await screen.findByRole("heading", { name: "Join Demo Crew" })).toBeInTheDocument();
    expect(screen.getByText("Ana invited you.")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "In the crew: Ana and Bogdan" })).toBeInTheDocument();
    expect(screen.getByText(/valid until November 10/)).toBeInTheDocument();
  });

  it("accepts, creates the account and goes to the welcome screen", async () => {
    mockGets({});
    post().mockImplementation((() => ok(meAs(ana), 201)) as never);
    renderRoutes(routes, { at: "/join/abc123" });

    await userEvent.click(await screen.findByRole("button", { name: "Accept the invite" }));
    expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("What should we call you?"), "Lena");
    await userEvent.type(screen.getByLabelText("Username"), "lena");
    await userEvent.type(screen.getByLabelText("Password"), "garden-flame-2026");
    await userEvent.click(screen.getByRole("button", { name: "Join the crew" }));

    expect(await screen.findByText("welcome page")).toBeInTheDocument();
    expect(api.POST).toHaveBeenCalledWith("/api/v1/invites/{code}/accept", {
      params: { path: { code: "abc123" } },
      body: {
        display_name: "Lena",
        username: "lena",
        password: "garden-flame-2026",
        preferred_language: "en",
      },
    });
  });

  it("shows field errors from the API next to the right field", async () => {
    mockGets({});
    post().mockImplementation((() =>
      fail(400, {
        code: "username_taken",
        fields: { username: ["This username is already taken."] },
      })) as never);
    renderRoutes(routes, { at: "/join/abc123" });

    await userEvent.click(await screen.findByRole("button", { name: "Accept the invite" }));
    await userEvent.type(screen.getByLabelText("What should we call you?"), "Ana");
    await userEvent.type(screen.getByLabelText("Username"), "ana");
    await userEvent.type(screen.getByLabelText("Password"), "garden-flame-2026");
    await userEvent.click(screen.getByRole("button", { name: "Join the crew" }));

    await waitFor(() =>
      expect(screen.getByLabelText("Username")).toHaveAccessibleDescription(
        "This username is already taken.",
      ),
    );
  });

  it("sends people with an account to login and back to the invite", async () => {
    mockGets({});
    const { router } = renderRoutes(routes, { at: "/join/abc123" });
    await userEvent.click(await screen.findByRole("button", { name: "I already have an account" }));
    expect(await screen.findByText("login page")).toBeInTheDocument();
    expect(router.state.location.search).toBe("?next=%2Fjoin%2Fabc123");
  });

  it("lets a logged-in person join with their account", async () => {
    mockGets({ me: meAs(bogdan) });
    post().mockImplementation((() => ok(meAs(bogdan), 201)) as never);
    renderRoutes(routes, { at: "/join/abc123" });

    expect(
      await screen.findByRole("heading", { name: "Join Demo Crew with your account" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/logged in as bogdan/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Join the crew" }));

    expect(await screen.findByText("welcome page")).toBeInTheDocument();
    expect(api.POST).toHaveBeenCalledWith("/api/v1/invites/{code}/join", {
      params: { path: { code: "abc123" } },
      body: { display_name: "Bogdan" },
    });
  });

  it("tells members they are already in the crew and opens it", async () => {
    mockGets({
      me: meAs(bogdan),
      invite: ok({ ...preview, already_member: true, crew_id: "c-1" }),
    });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(meAs(bogdan))) as never);
    const { router } = renderRoutes(routes, { at: "/join/abc123" });
    expect(
      await screen.findByRole("heading", { name: "You're already in Demo Crew" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open Demo Crew" }));
    expect(await screen.findByText("home page")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
    expect(put).toHaveBeenCalledWith("/api/v1/me/crew", { body: { crew_id: "c-1" } });
  });

  it("explains when you are already in the crew", async () => {
    mockGets({ me: meAs(bogdan) });
    post().mockImplementation((() => fail(409, { code: "already_member" })) as never);
    renderRoutes(routes, { at: "/join/abc123" });
    await userEvent.click(await screen.findByRole("button", { name: "Join the crew" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("You're already in this crew.");
  });

  it.each([
    ["expired", "The link has expired."],
    ["used", "The link was already used."],
  ])("explains a %s invite", async (status, text) => {
    mockGets({
      invite: ok({ ...preview, status, invited_by: null, members: [] }),
    });
    renderRoutes(routes, { at: "/join/abc123" });
    expect(
      await screen.findByRole("heading", { name: "This invite no longer works" }),
    ).toBeInTheDocument();
    expect(screen.getByText(new RegExp(text))).toBeInTheDocument();
  });

  it("explains an unknown or cancelled invite", async () => {
    mockGets({ invite: fail(404, { code: "invite_not_found" }) });
    renderRoutes(routes, { at: "/join/nope" });
    expect(await screen.findByText(/doesn't exist or was cancelled/)).toBeInTheDocument();
  });
});

describe("welcome", () => {
  it("greets the new member and opens Today on Start", async () => {
    get().mockImplementation((() => ok(meAs(bogdan))) as never);
    const { router } = renderRoutes(
      [
        { path: "/welcome", element: <WelcomeRoute /> },
        { path: "/", element: <p>home page</p> },
      ],
      { at: "/welcome" },
    );
    expect(await screen.findByRole("heading", { name: "Welcome, Bogdan" })).toBeInTheDocument();
    expect(screen.getByText("In the crew's time zone: Europe/Chisinau.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(await screen.findByText("home page")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });
});
