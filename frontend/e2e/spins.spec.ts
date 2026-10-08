import { expect, test } from "@playwright/test";

// The Wheel of Doom against the real backend: seed_demo_spins (playwright.config.ts) leaves every
// demo member three spins from last week of "Roata (demo)", whose punishments need no proof. Dan
// spins one, serves it with "Gata", and the crew sees it in the journal. Every seed starts over.
// Demo accounts use Romanian; reduced motion stops the dial at once.

const PASSWORD = "garden-flame-2026";

test("spin the wheel, serve the punishment, and the crew sees it", async ({ browser }) => {
  const page = await (
    await browser.newContext({ locale: "en-US", reducedMotion: "reduce" })
  ).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill("dan");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);

  await expect(page.getByRole("heading", { name: /\d+ (de )?rotir/ })).toBeVisible();
  await page.getByRole("button", { name: "Deschide" }).click();
  await expect(page).toHaveURL(/\/spins$/);

  await page.getByRole("button", { name: "Învârte" }).first().click();
  const result = page
    .getByRole("status")
    .filter({ has: page.getByRole("heading") })
    .first();
  await expect(result).toBeVisible();
  const punishment = (await result.getByRole("heading").textContent()) ?? "";
  await page.getByRole("button", { name: "Gata" }).first().click();
  await expect(page.getByText("Făcut", { exact: true })).toBeVisible();

  await page.goto("/crew");
  const card = page.getByRole("article").filter({ hasText: "Dan și-a făcut pedeapsa" }).first();
  await expect(card).toBeVisible();
  await expect(card.getByText(punishment)).toBeVisible();
});
