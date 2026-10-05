import { expect, test, type Browser, type Page } from "@playwright/test";

// The proposal pool against the real backend and the demo crew from `make seed` (ana is the
// admin, bogdan a member). Demo accounts use Romanian. Every run schedules one challenge for the
// next month and leaves nothing else behind in the pool.

const PASSWORD = "garden-flame-2026";

function unique(prefix: string): string {
  return `${prefix} ${Date.now().toString(36)}${Math.floor(Math.random() * 1000)}`;
}

async function logIn(browser: Browser, username: string): Promise<Page> {
  const page = await (await browser.newContext({ locale: "en-US" })).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
  return page;
}

/** The proposal's card on /challenges (the innermost section holding its link). */
function card(page: Page, title: string) {
  return page
    .locator("section")
    .filter({ has: page.getByRole("link", { name: title }) })
    .last();
}

/** Go through the wizard steps after the first one and press the final button. */
async function finishWizard(page: Page, finalButton: string) {
  for (const heading of ["Cât de des?", "Ce notezi la bifă?", "Ce dovadă cerem?", "Verifică"]) {
    await page.getByRole("button", { name: "Continuă" }).click();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await page.getByRole("button", { name: finalButton }).click();
  await expect(page).toHaveURL(/\/challenges\/[0-9a-f-]{36}$/);
}

async function propose(page: Page, title: string): Promise<string> {
  await page.goto("/challenges/new");
  await page.getByLabel("Numele provocării").fill(title);
  await finishWizard(page, "Publică propunerea");
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  return page.url();
}

/** As an admin on /challenges: choose the default month (the next whole month) for a proposal. */
async function schedule(page: Page, title: string) {
  await page.goto("/challenges");
  await card(page, title).getByRole("button", { name: "Alege", exact: true }).click();
  const sheet = page.getByRole("dialog");
  await sheet.getByRole("button", { name: /Alege pentru/ }).click();
  await expect(page.getByText(/Programată pentru/)).toBeVisible();
}

test("members propose and vote, edits reset votes, an admin schedules two for one month", async ({
  browser,
}) => {
  const walk = unique("Plimbare");
  const read = unique("Citit");
  const bogdan = await logIn(browser, "bogdan");

  await bogdan.goto("/challenges/new");
  await bogdan.getByRole("button", { name: "Continuă" }).click();
  await expect(bogdan.getByText("Dă-i un nume provocării.")).toBeVisible();
  const walkUrl = await propose(bogdan, walk);
  await expect(bogdan.getByText(/Propusă de Bogdan/)).toBeVisible();
  const readUrl = await propose(bogdan, read);

  const ana = await logIn(browser, "ana");
  await ana.goto("/challenges");
  await card(ana, walk).getByRole("button", { name: "Votează" }).click();
  await card(ana, read).getByRole("button", { name: "Votează" }).click();
  await expect(card(ana, walk).getByRole("button", { name: "Ai votat" })).toBeVisible();
  await expect(card(ana, read).getByText("Voturi: 1")).toBeVisible();

  const edited = `${walk} zilnic`;
  await bogdan.goto(walkUrl);
  await bogdan.getByRole("button", { name: "Modifică propunerea" }).click();
  await expect(bogdan.getByLabel("Numele provocării")).toHaveValue(walk);
  await bogdan.getByLabel("Numele provocării").fill(edited);
  await finishWizard(bogdan, "Salvează modificările");
  await expect(bogdan.getByRole("heading", { name: edited })).toBeVisible();

  await ana.reload();
  await expect(card(ana, edited).getByText("Voturi: 0")).toBeVisible();
  await expect(card(ana, read).getByText("Voturi: 1")).toBeVisible();

  await schedule(ana, edited);
  await schedule(ana, read);
  await ana.reload();
  await expect(ana.getByRole("link", { name: edited })).toHaveCount(1);
  await expect(ana.getByRole("link", { name: read })).toHaveCount(1);
  await expect(ana.getByRole("link", { name: edited })).toContainText("Urmează");

  await bogdan.goto(walkUrl);
  await expect(bogdan.getByText("Urmează")).toBeVisible();
  await expect(bogdan.getByRole("button", { name: "Modifică propunerea" })).toHaveCount(0);
  await bogdan.getByRole("button", { name: "Nu particip" }).click();
  await expect(bogdan.getByRole("button", { name: "Particip" })).toBeVisible();
  await bogdan.getByRole("button", { name: "Particip" }).click();
  await expect(bogdan.getByRole("button", { name: "Nu particip" })).toBeVisible();

  // The admin puts one back in the pool, then withdraws it (keeps the demo pool small).
  await ana.goto(readUrl);
  await ana.getByRole("button", { name: "Înapoi la propuneri" }).click();
  await expect(ana.getByText("E din nou printre propuneri")).toBeVisible();
  await expect(ana.getByRole("button", { name: "Ai votat" })).toBeVisible(); // the old vote is back
  await ana.getByRole("button", { name: "Retrage propunerea" }).click();
  await ana.getByRole("dialog").getByRole("button", { name: "Retrage propunerea" }).click();
  await expect(ana).toHaveURL(/\/challenges$/);
  await expect(ana.getByRole("link", { name: read })).toHaveCount(0);
});
