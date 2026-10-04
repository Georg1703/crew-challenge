import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { RequireAuth } from "@/app/RequireAuth";
import { fail, ok, renderRoutes } from "@/test/render";
import { ana, meAs } from "@/test/fixtures";

import { JoinRoute, LoginRoute } from ".";

const get = () => vi.spyOn(api, "GET");
const post = () => vi.spyOn(api, "POST");

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

    await userEvent.type(await screen.findByLabelText("Username"), "ana");
    await userEvent.type(screen.getByLabelText("Password"), "garden-flame-2026");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("crew page")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/crew");
    expect(api.POST).toHaveBeenCalledWith("/api/v1/auth/login", {
      body: { username: "ana", password: "garden-flame-2026" },
    });
  });

  it("shows a translated message for wrong credentials", async () => {
    get().mockImplementation((() => fail(401, { code: "not_authenticated" })) as never);
    post().mockImplementation((() => fail(400, { code: "invalid_credentials" })) as never);
    renderRoutes([{ path: "/login", element: <LoginRoute /> }], { at: "/login" });

    await userEvent.type(await screen.findByLabelText("Username"), "ana");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong username or password.");
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
});

describe("join", () => {
  const routes = [
    { path: "/join/:code", element: <JoinRoute /> },
    { path: "/", element: <p>home page</p> },
    { path: "/login", element: <p>login page</p> },
  ];

  it("creates the account and lands on home", async () => {
    get().mockImplementation((() =>
      ok({
        crew_name: "Demo Crew",
        status: "valid",
        expires_at: "2026-11-10T10:00:00Z",
      })) as never);
    post().mockImplementation((() => ok(meAs(ana), 201)) as never);
    renderRoutes(routes, { at: "/join/abc123" });

    expect(await screen.findByText("You're invited to Demo Crew")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("How the others see you"), "Ana");
    await userEvent.type(screen.getByLabelText("Username"), "ana");
    await userEvent.type(screen.getByLabelText("Password"), "garden-flame-2026");
    await userEvent.click(screen.getByRole("button", { name: "Join the crew" }));

    expect(await screen.findByText("home page")).toBeInTheDocument();
  });

  it("shows field errors from the API next to the right field", async () => {
    get().mockImplementation((() =>
      ok({
        crew_name: "Demo Crew",
        status: "valid",
        expires_at: "2026-11-10T10:00:00Z",
      })) as never);
    post().mockImplementation((() =>
      fail(400, {
        code: "username_taken",
        fields: { username: ["This username is already taken."] },
      })) as never);
    renderRoutes(routes, { at: "/join/abc123" });

    await userEvent.type(await screen.findByLabelText("How the others see you"), "Ana");
    await userEvent.type(screen.getByLabelText("Username"), "ana");
    await userEvent.type(screen.getByLabelText("Password"), "garden-flame-2026");
    await userEvent.click(screen.getByRole("button", { name: "Join the crew" }));

    await waitFor(() =>
      expect(screen.getByLabelText("Username")).toHaveAccessibleDescription(
        "This username is already taken.",
      ),
    );
  });

  it.each([
    ["expired", "The link has expired."],
    ["used", "The link was already used."],
  ])("explains a %s invite", async (status, text) => {
    get().mockImplementation((() =>
      ok({ crew_name: "Demo Crew", status, expires_at: "2026-11-10T10:00:00Z" })) as never);
    renderRoutes(routes, { at: "/join/abc123" });
    expect(await screen.findByText(new RegExp(text))).toBeInTheDocument();
  });

  it("explains an unknown invite", async () => {
    get().mockImplementation((() => fail(404, { code: "invite_not_found" })) as never);
    renderRoutes(routes, { at: "/join/nope" });
    expect(await screen.findByText(/The link doesn't exist/)).toBeInTheDocument();
  });
});
