import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { i18n } from "@/i18n";
import { ok, renderRoutes } from "@/test/render";
import { ana, bogdan, meAs } from "@/test/fixtures";

import { MeRoute } from ".";

describe("me screen", () => {
  it("switches the language and saves it to the account", async () => {
    vi.spyOn(api, "GET").mockImplementation((() => ok(meAs(ana))) as never);
    const patch = vi.spyOn(api, "PATCH").mockImplementation((() => ok(meAs(ana, "ro"))) as never);
    renderRoutes([{ path: "/", element: <MeRoute /> }]);

    await userEvent.click(await screen.findByLabelText("Română"));

    expect(patch).toHaveBeenCalledWith("/api/v1/me", { body: { preferred_language: "ro" } });
    expect(await screen.findByText("Limba")).toBeInTheDocument();
    await i18n.changeLanguage("en");
  });

  it("logs out and goes to the login page", async () => {
    vi.spyOn(api, "GET").mockImplementation((() => ok(meAs(ana))) as never);
    vi.spyOn(api, "POST").mockImplementation((() => ok(undefined, 204)) as never);
    const { router } = renderRoutes([
      { path: "/", element: <MeRoute /> },
      { path: "/login", element: <p>login page</p> },
    ]);

    await userEvent.click(await screen.findByRole("button", { name: "Log out" }));
    expect(await screen.findByText("login page")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("lists every crew and switches to another one", async () => {
    const inTwo = {
      ...meAs(bogdan),
      crews: [
        {
          crew_id: "33333333-3333-3333-3333-333333333333",
          crew_name: "Demo Crew",
          display_name: "Bogdan",
          role: "member",
        },
        { crew_id: "c-eva", crew_name: "Echipa Eva", display_name: "Bogdan E", role: "member" },
      ],
    };
    vi.spyOn(api, "GET").mockImplementation((() => ok(inTwo)) as never);
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(inTwo)) as never);
    renderRoutes([{ path: "/", element: <MeRoute /> }]);

    const crews = await screen.findByRole("list", { name: "My crews" });
    expect(within(crews).getByText("Current")).toBeInTheDocument();
    await userEvent.click(within(crews).getByRole("button", { name: /Echipa Eva/ }));
    expect(put).toHaveBeenCalledWith("/api/v1/me/crew", { body: { crew_id: "c-eva" } });
    expect(await screen.findByText("Switched to Echipa Eva")).toBeInTheDocument();
  });

  it("hides the crew list for people in one crew", async () => {
    vi.spyOn(api, "GET").mockImplementation((() => ok(meAs(ana))) as never);
    renderRoutes([{ path: "/", element: <MeRoute /> }]);
    await screen.findByText("Language");
    expect(screen.queryByRole("list", { name: "My crews" })).not.toBeInTheDocument();
  });
});
