import { expect, test, type Browser, type Page } from "@playwright/test";

// Proposing, voting and choosing a monthly challenge against the real backend and the demo crew
// from `make seed` (ana is the admin, bogdan a member). Demo accounts use Romanian.
// Choosing closes the open round, so every run works on the next month that is still open.

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

test("a member proposes, the crew votes, an edit resets the votes and the admin chooses", async ({
  browser,
}) => {
  const title = unique("Plimbare");
  const bogdan = await logIn(browser, "bogdan");

  await bogdan.goto("/challenges");
  await bogdan.getByRole("button", { name: "Propune o provocare" }).click();
  await bogdan.getByRole("button", { name: "Continuă" }).click();
  await expect(bogdan.getByText("Dă-i un nume provocării.")).toBeVisible();
  await bogdan.getByLabel("Numele provocării").fill(title);
  await finishWizard(bogdan, "Publică propunerea");
  await expect(bogdan.getByRole("heading", { name: title })).toBeVisible();
  await expect(bogdan.getByText(/Propusă de Bogdan/)).toBeVisible();
  const challengeUrl = bogdan.url();

  const ana = await logIn(browser, "ana");
  await ana.goto("/challenges");
  await card(ana, title).getByRole("button", { name: "Votează" }).click();
  await expect(card(ana, title).getByRole("button", { name: "Votul tău" })).toBeVisible();
  await expect(card(ana, title).getByText("Voturi: 1")).toBeVisible();

  const edited = `${title} zilnic`;
  await bogdan.goto(challengeUrl);
  await bogdan.getByRole("button", { name: "Modifică propunerea" }).click();
  await expect(bogdan.getByLabel("Numele provocării")).toHaveValue(title);
  await bogdan.getByLabel("Numele provocării").fill(edited);
  await finishWizard(bogdan, "Salvează modificările");
  await expect(bogdan.getByRole("heading", { name: edited })).toBeVisible();

  await ana.reload();
  await expect(card(ana, edited).getByText("Voturi: 0")).toBeVisible();
  await card(ana, edited).getByRole("button", { name: "Alege-o" }).click();
  await ana.getByRole("dialog").getByRole("button", { name: "Alege provocarea" }).click();
  await expect(ana.getByText(/Provocarea pentru .+ e aleasă/)).toBeVisible();

  await bogdan.goto(challengeUrl);
  await expect(bogdan.getByText("Urmează")).toBeVisible();
  await expect(bogdan.getByRole("button", { name: "Modifică propunerea" })).toHaveCount(0);
  await bogdan.getByRole("button", { name: "Nu particip" }).click();
  await expect(bogdan.getByRole("button", { name: "Particip" })).toBeVisible();
  await bogdan.getByRole("button", { name: "Particip" }).click();
  await expect(bogdan.getByRole("button", { name: "Nu particip" })).toBeVisible();
});
