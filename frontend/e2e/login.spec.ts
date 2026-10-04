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

  await expect(page.getByRole("heading", { name: "Bună, Ana" })).toBeVisible();
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
