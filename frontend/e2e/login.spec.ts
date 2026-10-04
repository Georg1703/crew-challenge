import { expect, test } from "@playwright/test";

const PASSWORD = "garden-flame-2026"; // the demo crew from `make seed`

// Before login the UI follows the browser (English here). After login it switches to the
// account's saved language, which is Romanian for new and demo accounts.

test("a member logs in and sees the crew on home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Username").fill("Ana");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(page.getByRole("heading", { name: "Salut, Ana!" })).toBeVisible();
  await expect(page.getByText("Demo Crew")).toBeVisible();
  for (const name of ["Ana", "Bogdan", "Cristina", "Dan"]) {
    await expect(
      page.getByRole("listitem").filter({ has: page.getByText(name, { exact: true }) }),
    ).toBeVisible();
  }

  await page.getByRole("link", { name: "Echipa" }).click();
  await expect(page).toHaveURL(/\/crew$/);
  await expect(page.getByRole("button", { name: "Invită pe cineva" })).toBeVisible();
});

test("a new person joins with an invite link", async ({ page, browser }) => {
  // The admin creates an invite.
  await page.goto("/login");
  await page.getByLabel("Username").fill("ana");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.getByRole("link", { name: "Echipa" }).click();
  await page.getByRole("button", { name: "Invită pe cineva" }).click();
  const link = await page.locator("output").textContent();
  expect(link).toMatch(/\/join\/\w+$/);

  // Someone else opens it in a fresh browser.
  const guest = await (await browser.newContext({ locale: "en-US" })).newPage();
  const username = `guest${Date.now()}`;
  await guest.goto(new URL(link ?? "", "http://localhost:5173").pathname);
  await expect(guest.getByRole("heading", { name: "You're invited to Demo Crew" })).toBeVisible();
  await guest.getByLabel("How the others see you").fill(`Guest ${Date.now() % 10000}`);
  await guest.getByLabel("Username").fill(username);
  await guest.getByLabel("Password").fill(PASSWORD);
  await guest.getByRole("button", { name: "Join the crew" }).click();
  await expect(guest.getByRole("heading", { name: /^Salut, Guest/ })).toBeVisible();
});
