import { expect, test, type Browser, type Locator, type Page } from "@playwright/test";

// The daily check-in against the real backend: `make seed` gives Demo Crew "Plimbare (demo)",
// running every day of the current month for everyone. Demo accounts use Romanian.
// The test leaves Dan's day as it found it (unchecked), so it can run again the same day.

const PASSWORD = "garden-flame-2026";
const WALK = "Plimbare (demo)";

async function logIn(browser: Browser, username: string): Promise<Page> {
  const page = await (await browser.newContext({ locale: "en-US" })).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
  return page;
}

/** Undo today's check-in for a challenge if there is one; true if something was undone. */
async function uncheck(page: Page, title: string): Promise<boolean> {
  const today = (await (await page.request.get("/api/v1/today")).json()) as {
    day: string;
    challenges: { id: string; title: string; state: string }[];
  };
  const challenge = today.challenges.find((c) => c.title === title);
  if (!challenge || challenge.state !== "done") return false;
  const csrf =
    (await page.context().cookies()).find((c) => c.name === "crew_csrftoken")?.value ?? "";
  await page.request.delete(`/api/v1/challenges/${challenge.id}/check-ins/${today.day}/last`, {
    headers: { "X-CSRFToken": csrf, Referer: page.url() },
  });
  return true;
}

/** The challenge's card on Today. */
function card(page: Page, title: string): Locator {
  return page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: title }) })
    .last();
}

/** Press and hold like a finger would (the button asks for 0.6 s). */
async function hold(page: Page, button: Locator) {
  await button.evaluate((el) => el.scrollIntoView({ block: "center" }));
  const box = await button.boundingBox();
  if (!box) throw new Error("hold button not visible");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(800);
  await page.mouse.up();
}

test("hold to check in, undo, and see the crew's month", async ({ browser }) => {
  const dan = await logIn(browser, "dan");
  const walk = card(dan, WALK);
  await expect(walk).toBeVisible();

  // A failed earlier run today may have left it checked: undo it through the API first.
  if (await uncheck(dan, WALK)) await dan.reload();

  const button = walk.getByRole("button", { name: "Ține apăsat ca să bifezi" });
  await expect(button).toBeVisible();

  // Letting go early does nothing.
  await button.evaluate((el) => el.scrollIntoView({ block: "center" }));
  const box = await button.boundingBox();
  if (!box) throw new Error("hold button not visible");
  await dan.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await dan.mouse.down();
  await dan.waitForTimeout(200);
  await dan.mouse.up();
  await expect(button).toBeVisible();

  await hold(dan, button);
  await expect(walk.getByRole("button", { name: "Bifat azi" })).toBeVisible();
  await expect(dan.getByRole("status").filter({ hasText: "Bifat" })).toBeVisible();

  // The crew row and the raised button follow.
  await expect(dan.getByRole("heading", { name: "Echipa azi" })).toBeVisible();

  await dan.getByRole("button", { name: "Anulează" }).first().click();
  await expect(dan.getByText("Am anulat")).toBeVisible();
  await expect(walk.getByRole("button", { name: "Ține apăsat ca să bifezi" })).toBeVisible();

  // The raised button opens what is left today.
  await dan.getByRole("button", { name: /^Bifează/ }).click();
  const sheet = dan.getByRole("dialog", { name: "Ce bifezi acum?" });
  await expect(sheet.getByRole("heading", { name: WALK })).toBeVisible();
  await sheet.getByRole("button", { name: "Închide" }).click();

  // The challenge page has the crew's month.
  await dan.goto("/challenges");
  await dan.getByRole("link").filter({ hasText: WALK }).first().click();
  await expect(dan.getByRole("table", { name: /Luna echipei/ })).toBeVisible();
});
