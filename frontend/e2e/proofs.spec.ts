import { expect, test, type Page } from "@playwright/test";

// A photo as proof, against the real backend with in-memory storage (playwright.config.ts). On a
// challenge that asks for proof the check-in waits for it: the photo uploads first, as a draft on
// today's card, then Cristina checks in and it shows in the crew feed on Echipa. Her day is
// cleared before and after (drafts deleted, posts undone with their proofs), so the test can run
// again the same day.

const PASSWORD = "garden-flame-2026";
const WALK = "Plimbare (demo)";
const PIXEL = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
); // a 1x1 PNG

type Day = {
  day: string;
  challenges: {
    id: string;
    title: string;
    state: string;
    proofs: { id: string; posted: boolean }[];
  }[];
};

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

/** Today's walk with nothing on it: its draft files deleted, its posts undone. */
async function clear(page: Page): Promise<{ id: string; day: string }> {
  for (;;) {
    const today = (await (await page.request.get("/api/v1/today")).json()) as Day;
    const walk = today.challenges.find((c) => c.title === WALK);
    if (!walk) throw new Error(`${WALK} is not running: make seed`);
    for (const draft of walk.proofs.filter((p) => !p.posted)) {
      await send(page, "delete", `/api/v1/proofs/${draft.id}`);
    }
    if (walk.state !== "done" && walk.state !== "partial") return { id: walk.id, day: today.day };
    await send(page, "delete", `/api/v1/challenges/${walk.id}/check-ins/${today.day}/last`);
  }
}

test("check in with a photo and see it in the crew feed", async ({ browser }) => {
  const page = await (await browser.newContext({ locale: "en-US" })).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill("cristina");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);

  await clear(page); // left by a failed run

  try {
    await page.reload();
    const card = page
      .locator("section")
      .filter({ has: page.getByRole("heading", { name: WALK }) })
      .last();
    const hold = card.getByRole("button", { name: "Ține apăsat ca să bifezi" });
    await expect(card.getByText("Adaugă o poză sau un video ca să bifezi")).toBeVisible();
    await expect(hold).toBeDisabled();
    await card
      .locator('input[accept="image/*"]')
      .setInputFiles({ name: "walk.png", mimeType: "image/png", buffer: PIXEL });

    // Saved: the tile now shows the copy read back from storage, not the one on the phone.
    const tile = card.getByRole("button", { name: "Poză. Atinge pentru a deschide" });
    await expect(tile).toBeVisible();
    await tile.scrollIntoViewIfNeeded(); // the thumbnail loads lazily
    await expect(tile.locator("img")).toHaveJSProperty("naturalWidth", 1);
    await tile.click();
    await expect(page.getByRole("dialog", { name: "Dovezi" })).toBeVisible();
    await page.keyboard.press("Escape");

    await expect(hold).toBeEnabled(); // uploaded: the check-in can go
    await hold.focus();
    await page.keyboard.press("Enter"); // the keyboard confirms at once
    await expect(card.getByRole("button", { name: "Bifat azi" })).toBeVisible();

    await page.goto("/crew");
    await expect(page.getByText("Cristina a bifat").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Poză de la Cristina" }).first()).toBeVisible();
  } finally {
    await clear(page);
  }
});
