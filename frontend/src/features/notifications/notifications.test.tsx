import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api";
import { ok, renderScreen } from "@/test/render";
import { ana, bogdan, crewDetail, meAs } from "@/test/fixtures";

import { NewsRoute, PushPrompt, PushToggle } from ".";
import { noteCheckIn, toKey } from "./push";

const CARD = "44444444-4444-4444-4444-444444444444";
const KEY =
  "BFYn-HSS6-6d-1NENPow1Nw0yFvzJjoeKYeHOkXCq7CJYgOt82ACVhl_fnUir8Ildl7qUBussQQHPbkjoSm0LgA";

const line = (id: string, kind: "reaction" | "comment" | "reply", facts: object, read = false) => ({
  id,
  kind,
  actor: bogdan,
  target: { type: "entry", id: CARD },
  facts,
  created_at: "2026-11-10T08:00:00Z",
  read_at: read ? "2026-11-10T09:00:00Z" : null,
});

function mockGets(news: unknown, publicKey = KEY) {
  vi.spyOn(api, "GET").mockImplementation(((path: string) => {
    if (path === "/api/v1/me") return ok(meAs(ana));
    if (path === "/api/v1/notifications") return ok(news);
    if (path === "/api/v1/push/key") return ok({ public_key: publicKey });
    return ok(crewDetail);
  }) as never);
}

describe("news screen", () => {
  it("lists what happened, latest first, opens the card and reads it all", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-10T12:00:00Z")); // the lines are from this morning
    mockGets({
      unread: 2,
      results: [
        line("n1", "reaction", { on: "entry", emoji: "\u{1F525}" }),
        line("n2", "reply", { on: "comment", text: "Si eu!" }),
        line("n3", "comment", { on: "entry", text: "Bravo" }, true),
        line("n4", "reaction", { on: "comment", emoji: "\u{1F44F}" }, true),
      ],
    });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(undefined, 204)) as never);
    renderScreen(<NewsRoute />, { path: "/crew/news" });

    const list = await screen.findByRole("list", { name: "News" });
    const rows = within(list).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      "BBogdan reacted with \u{1F525} to your post10:00 AMNew",
      "BBogdan answered youSi eu! - 10:00 AMNew",
      "BBogdan commentedBravo - 10:00 AM",
      "BBogdan reacted with \u{1F44F} to your comment10:00 AM",
    ]);
    expect(within(list).getAllByRole("link")[0]).toHaveAttribute("href", `/crew/cards/${CARD}`);
    await waitFor(() => expect(put).toHaveBeenCalledWith("/api/v1/notifications/read"));
    vi.useRealTimers();
  });

  it("says when there is nothing yet and reads nothing", async () => {
    mockGets({ unread: 0, results: [] });
    const put = vi.spyOn(api, "PUT");
    renderScreen(<NewsRoute />, { path: "/crew/news" });
    expect(await screen.findByText(/Nothing new yet/)).toBeInTheDocument();
    expect(put).not.toHaveBeenCalled();
  });
});

type FakeSubscription = {
  endpoint: string;
  toJSON: () => object;
  unsubscribe: () => Promise<boolean>;
};

function fakeBrowser({
  permission = "default" as NotificationPermission,
  subscription = null as FakeSubscription | null,
} = {}) {
  const subscribe = vi.fn(async () => {
    subscription = {
      endpoint: "https://push.example/abc",
      toJSON: () => ({ endpoint: "https://push.example/abc", keys: { p256dh: "p", auth: "a" } }),
      unsubscribe: async () => true,
    };
    return subscription;
  });
  const notification = {
    permission,
    requestPermission: vi.fn(async () => {
      notification.permission = "granted";
      return "granted" as NotificationPermission;
    }),
  };
  const registration = { pushManager: { getSubscription: async () => subscription, subscribe } };
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: { ready: Promise.resolve(registration) },
  });
  vi.stubGlobal("PushManager", function PushManager() {});
  vi.stubGlobal("Notification", notification);
  return { subscribe, notification };
}

afterEach(() => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  delete (navigator as any).serviceWorker;
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("push switch", () => {
  it("is not there when the browser cannot push", async () => {
    mockGets({ unread: 0, results: [] });
    renderScreen(<PushToggle />);
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });

  it("asks for permission, subscribes and tells the server; off again forgets it", async () => {
    const { subscribe, notification } = fakeBrowser();
    mockGets({ unread: 0, results: [] });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(undefined, 204)) as never);
    const del = vi.spyOn(api, "DELETE").mockImplementation((() => ok(undefined, 204)) as never);
    renderScreen(<PushToggle />);

    const toggle = await screen.findByRole("switch", { name: /Notifications on this device/ });
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    await waitFor(() => expect(toggle).toBeChecked());
    expect(notification.requestPermission).toHaveBeenCalled();
    expect(subscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: toKey(KEY),
    });
    expect(put).toHaveBeenCalledWith("/api/v1/push/subscriptions", {
      body: { endpoint: "https://push.example/abc", keys: { p256dh: "p", auth: "a" } },
    });

    await userEvent.click(toggle);
    await waitFor(() => expect(toggle).not.toBeChecked());
    expect(del).toHaveBeenCalledWith("/api/v1/push/subscriptions", {
      params: { query: { endpoint: "https://push.example/abc" } },
    });
  });

  it("explains when the browser blocked it, and hides when the server has no key", async () => {
    fakeBrowser({ permission: "denied" });
    mockGets({ unread: 0, results: [] });
    renderScreen(<PushToggle />);
    expect(await screen.findByText(/Blocked in the browser/)).toBeInTheDocument();
    expect(screen.getByRole("switch")).not.toBeChecked();

    mockGets({ unread: 0, results: [] }, "");
    renderScreen(<PushToggle />);
    await waitFor(() => expect(api.GET).toHaveBeenCalledWith("/api/v1/push/key"));
    expect(screen.getAllByRole("switch")).toHaveLength(1); // only the first render's
  });
});

describe("push switch on an iPhone in Safari", () => {
  it("shows the install hint instead of a switch (Safari has no PushManager)", async () => {
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
    );
    mockGets({ unread: 0, results: [] });
    renderScreen(<PushToggle />);
    expect(await screen.findByText(/Install the app on your Home Screen/)).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });
});

describe("push prompt", () => {
  it("waits for a check-in on this device, then offers once and goes away for two weeks", async () => {
    fakeBrowser();
    mockGets({ unread: 0, results: [] });
    vi.spyOn(api, "PUT").mockImplementation((() => ok(undefined, 204)) as never);
    const { unmount } = renderScreen(<PushPrompt />);
    await waitFor(() => expect(api.GET).toHaveBeenCalledWith("/api/v1/push/key"));
    expect(screen.queryByText(/Want to know/)).not.toBeInTheDocument();
    unmount();

    noteCheckIn();
    renderScreen(<PushPrompt />);
    expect(await screen.findByText(/Want to know/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByText(/Want to know/)).not.toBeInTheDocument();
    expect(localStorage.getItem("push-prompt-dismissed-at")).not.toBeNull();
  });

  it("turns push on from the prompt", async () => {
    fakeBrowser();
    noteCheckIn();
    mockGets({ unread: 0, results: [] });
    const put = vi.spyOn(api, "PUT").mockImplementation((() => ok(undefined, 204)) as never);
    renderScreen(<PushPrompt />);
    await userEvent.click(await screen.findByRole("button", { name: "Turn on" }));
    await waitFor(() =>
      expect(put).toHaveBeenCalledWith("/api/v1/push/subscriptions", expect.anything()),
    );
    await waitFor(() => expect(screen.queryByText(/Want to know/)).not.toBeInTheDocument());
  });
});

describe("the push key", () => {
  it("is 65 bytes of P-256 point once decoded", () => {
    expect(toKey(KEY)).toHaveLength(65);
    expect(toKey(KEY)[0]).toBe(4);
  });
});
