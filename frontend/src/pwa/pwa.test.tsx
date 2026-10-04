import { act, render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/app/providers";
import { createQueryClient } from "@/app/queryClient";
import { pwaMock } from "@/test/pwaRegisterMock";

import { captureInstallPrompt, resetInstallPrompt } from "./installPrompt";
import { InstallCard } from "./InstallCard";
import { detectPlatform } from "./platform";
import { UpdateBanner } from "./UpdateBanner";

const IPHONE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const IPAD =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15";
const ANDROID =
  "Mozilla/5.0 (Linux; Android 15; Pixel 7) AppleWebKit/537.36 Chrome/141.0 Mobile Safari/537.36";
const notStandalone = () => ({ matches: false });

function renderUi(ui: React.ReactNode) {
  return render(<Providers client={createQueryClient()}>{ui}</Providers>);
}

function setUserAgent(ua: string) {
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue(ua);
}

describe("detectPlatform", () => {
  it.each([
    ["iPhone", { userAgent: IPHONE, maxTouchPoints: 5 }, true],
    ["iPad (reports Mac + touch)", { userAgent: IPAD, maxTouchPoints: 5 }, true],
    ["Mac", { userAgent: IPAD, maxTouchPoints: 0 }, false],
    ["Android", { userAgent: ANDROID, maxTouchPoints: 5 }, false],
  ])("%s", (_name, nav, ios) => {
    expect(detectPlatform(nav, notStandalone)).toEqual({ ios, standalone: false });
  });

  it("knows when it runs as an installed app", () => {
    const nav = { userAgent: IPHONE, maxTouchPoints: 5, standalone: true };
    expect(detectPlatform(nav, notStandalone).standalone).toBe(true);
    expect(
      detectPlatform({ userAgent: ANDROID, maxTouchPoints: 5 }, () => ({ matches: true }))
        .standalone,
    ).toBe(true);
  });
});

describe("InstallCard", () => {
  beforeEach(() => {
    resetInstallPrompt();
    localStorage.clear();
  });
  afterEach(() => resetInstallPrompt());

  it("is hidden when the browser cannot install", () => {
    setUserAgent(ANDROID);
    renderUi(<InstallCard />);
    expect(screen.queryByText("Install the app")).not.toBeInTheDocument();
  });

  it("opens the browser's install dialog on Android", async () => {
    setUserAgent(ANDROID);
    const target = new EventTarget() as Window;
    captureInstallPrompt(target);
    const prompt = vi.fn(async () => undefined);
    const event = Object.assign(new Event("beforeinstallprompt", { cancelable: true }), {
      prompt,
      userChoice: Promise.resolve({ outcome: "accepted" as const }),
    });

    renderUi(<InstallCard />);
    act(() => void target.dispatchEvent(event));
    expect(event.defaultPrevented).toBe(true);

    await userEvent.click(screen.getByRole("button", { name: "Install" }));
    expect(prompt).toHaveBeenCalled();
    expect(screen.queryByText("Install the app")).not.toBeInTheDocument();
  });

  it("shows the Add to Home Screen steps on iPhone", async () => {
    setUserAgent(IPHONE);
    renderUi(<InstallCard />);
    await userEvent.click(screen.getByRole("button", { name: "Install" }));

    const guide = await screen.findByRole("dialog", { name: "Add it to your Home Screen" });
    expect(guide).toHaveTextContent("Tap the Share button");
    expect(guide).toHaveTextContent("Add to Home Screen");
    expect(guide).toHaveTextContent("Tap “Add”");
  });

  it("'Not now' hides the card and remembers it on this device", async () => {
    setUserAgent(IPHONE);
    const { unmount } = renderUi(<InstallCard dismissible />);
    await userEvent.click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByText("Install the app")).not.toBeInTheDocument();
    unmount();

    renderUi(<InstallCard dismissible />);
    expect(screen.queryByText("Install the app")).not.toBeInTheDocument();
  });
});

describe("UpdateBanner", () => {
  afterEach(() => {
    pwaMock.needRefresh = false;
  });

  it("stays hidden until a new version is waiting", () => {
    renderUi(<UpdateBanner />);
    expect(screen.queryByText("A new version of the app is ready.")).not.toBeInTheDocument();
  });

  it("updates when the user taps Update", async () => {
    pwaMock.needRefresh = true;
    renderUi(<UpdateBanner />);
    expect(screen.getByText("A new version of the app is ready.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Update" }));
    expect(pwaMock.updateServiceWorker).toHaveBeenCalledWith(true);
  });

  it("can be postponed", async () => {
    pwaMock.needRefresh = true;
    renderUi(<UpdateBanner />);
    await userEvent.click(screen.getByRole("button", { name: "Later" }));
    // The banner slides out before it leaves the page.
    await waitForElementToBeRemoved(() => screen.queryByText("A new version of the app is ready."));
  });
});
