import { expect, test } from "@playwright/test";

// The Wheel of Doom against the real backend: seed_demo_spins (playwright.config.ts) leaves every
// demo member three spins from last week of "Roata (demo)", whose punishments need no proof. Dan
// spins one, serves it with "Gata", and the crew sees it in the journal. Every seed starts over.
// Demo accounts use Romanian; reduced motion stops the dial at once. Locally the database is the
// dev one, so Dan may owe other spins too: everything here stays on the Roata cards.

const PASSWORD = "garden-flame-2026";

test("spin the wheel, serve the punishment, and the crew sees it", async ({ browser }) => {
  const page = await (
    await browser.newContext({ locale: "en-US", reducedMotion: "reduce" })
  ).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill("dan");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);

  const owed = page.getByRole("heading", { name: /\d+ (de )?rotir/ });
  await expect(owed).toBeVisible();
  await owed.click();
  await expect(page).toHaveURL(/\/spins$/);

  const roata = page.locator("section").filter({ hasText: "Roata (demo)" });
  await roata.getByRole("button", { name: "Învârte" }).first().click();
  const result = page.getByRole("status").filter({ has: page.getByRole("heading") });
  const spun = roata.filter({ has: result }).last(); // the one card that just landed
  await expect(spun).toBeVisible();
  const punishment = (await spun.getByRole("status").getByRole("heading").textContent()) ?? "";
  await spun.getByRole("button", { name: "Gata" }).click();
  await expect(page.getByText("Făcut", { exact: true })).toBeVisible();

  await page.goto("/crew");
  const card = page
    .getByRole("article")
    .filter({ hasText: "Dan și-a făcut pedeapsa" })
    .filter({ hasText: punishment })
    .first();
  await expect(card).toBeVisible();
});
