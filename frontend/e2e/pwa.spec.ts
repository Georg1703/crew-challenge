import { expect, test } from "@playwright/test";

test("the production build is installable, starts offline and never caches the API", async ({
  page,
  context,
}) => {
  await page.goto("/login");

  // The service worker installs, then controls the page after a reload.
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect
    .poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller)))
    .toBe(true);

  // Chrome's own installability check (the one behind the install prompt) finds no problems.
  const cdp = await context.newCDPSession(page);
  const { installabilityErrors } = await cdp.send("Page.getInstallabilityErrors");
  expect(installabilityErrors).toEqual([]);

  const manifest = (await page.evaluate(async () =>
    (await fetch("/manifest.webmanifest")).json(),
  )) as { icons: { sizes: string; purpose?: string }[] };
  expect(manifest).toMatchObject({ display: "standalone", start_url: "/", lang: "ro" });
  expect(manifest.icons.map((icon) => icon.purpose ?? icon.sizes)).toEqual([
    "192x192",
    "512x512",
    "maskable",
  ]);

  // Offline: the app shell still starts (from the precache)...
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();

  // ...but API requests are never answered from a cache.
  const apiAnswered = await page.evaluate(() =>
    fetch("/api/health").then(
      (response) => response.ok,
      () => false,
    ),
  );
  expect(apiAnswered).toBe(false);
  await context.setOffline(false);
});
