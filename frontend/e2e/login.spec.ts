import { expect, test } from "@playwright/test";

const PASSWORD = "garden-flame-2026"; // the demo crew from `make seed`

// Before login the UI follows the browser (English here). After login it switches to the
// account's saved language, which is Romanian for new and demo accounts.

test("a member logs in, sees today's challenges and finds the crew in its tab", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Username").fill("Ana");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(page.getByRole("heading", { name: "Bună, Ana" })).toBeVisible();
  await expect(page.getByText("Propuneri pentru următoarele provocări")).toHaveCount(0);
  await expect(page.getByRole("list", { name: "Membrii echipei" })).toHaveCount(0);

  await page.getByRole("link", { name: "Echipa" }).click();
  await expect(page).toHaveURL(/\/crew$/);
  await expect(page.getByRole("heading", { name: "Demo Crew" })).toBeVisible();
  const stories = page.getByRole("list", { name: "Azi în echipă" });
  for (const name of ["Tu", "Bogdan", "Cristina", "Dan"]) {
    await expect(stories.getByText(name, { exact: true })).toBeVisible();
  }
  await page.getByRole("button", { name: "Membri și invitații" }).click();
  await expect(page.getByRole("button", { name: "Invită pe cineva" })).toBeVisible();
});
