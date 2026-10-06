import { expect, test, type Page } from "@playwright/test";

// A photo as proof, against the real backend with in-memory storage (playwright.config.ts): it
// shows on today's card and in the crew feed on Echipa. Cristina checks in through the API and her
// check-in is undone at the end (undo takes its proofs), so the test can run again the same day.

const PASSWORD = "garden-flame-2026";
const WALK = "Plimbare (demo)";
const PIXEL = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
); // a 1x1 PNG

/** The API as the SPA calls it: with the CSRF token. */
async function send(page: Page, method: "post" | "delete", path: string, data?: object) {
  const csrf =
    (await page.context().cookies()).find((c) => c.name === "crew_csrftoken")?.value ?? "";
  const response = await page.request.fetch(path, {
    method,
    data,
    headers: { "X-CSRFToken": csrf, Referer: page.url() },
  });
  expect(response.ok()).toBe(true);
}

test("add a photo to today's check-in and see it in the crew feed", async ({ browser }) => {
  const page = await (await browser.newContext({ locale: "en-US" })).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill("cristina");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);

  const today = (await (await page.request.get("/api/v1/today")).json()) as {
    day: string;
    challenges: { id: string; title: string; state: string }[];
  };
  const walk = today.challenges.find((c) => c.title === WALK);
  if (!walk) throw new Error(`${WALK} is not running: make seed`);
  const undo = `/api/v1/challenges/${walk.id}/check-ins/${today.day}/last`;
  if (walk.state === "done") await send(page, "delete", undo); // left by a failed run
  await send(page, "post", `/api/v1/challenges/${walk.id}/check-ins`, { day: today.day });

  try {
    await page.reload();
    const card = page
      .locator("section")
      .filter({ has: page.getByRole("heading", { name: WALK }) })
      .last();
    await card
      .locator('input[type="file"]')
      .setInputFiles({ name: "walk.png", mimeType: "image/png", buffer: PIXEL });

    // Saved: the tile now shows the copy read back from storage, not the one on the phone.
    const tile = card.getByRole("button", { name: "Poză. Atinge pentru a deschide" });
    await expect(tile).toBeVisible();
    await tile.scrollIntoViewIfNeeded(); // the thumbnail loads lazily
    await expect(tile.locator("img")).toHaveJSProperty("naturalWidth", 1);
    await tile.click();
    await expect(page.getByRole("dialog", { name: "Dovezi" })).toBeVisible();
    await page.keyboard.press("Escape");

    await page.goto("/crew");
    await expect(page.getByText("Cristina a bifat").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Poză de la Cristina" }).first()).toBeVisible();
  } finally {
    await send(page, "delete", undo);
  }
});
