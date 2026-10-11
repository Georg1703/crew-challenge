import { devices, expect, test, type Browser, type Locator, type Page } from "@playwright/test";

// Comments on a card's page against the real backend and the demo crew (`make seed`): Dan, on a
// phone, comments on a card of an earlier day and goes back to the feed; Cristina, on a computer,
// replies (her message quotes his); Dan's feed marks the card as having something new until he
// opens it; he reacts to his comment by holding it; her deleted reply leaves his open page within
// seconds. Then each deletes theirs
// in its first minute (hers first: his has a reply until then). An earlier day's card, so no test
// that undoes today's posts finds comments on it; the texts are new each run.

const PASSWORD = "garden-flame-2026";
const FIRE = "\u{1F525}";

/** A new session; the project's phone unless `device` says otherwise. */
async function logIn(browser: Browser, username: string, device = {}): Promise<Page> {
  const page = await (await browser.newContext({ ...device, locale: "en-US" })).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
  return page;
}

/** Hold like a finger: the menu opens after half a second. */
async function hold(page: Page, target: Locator): Promise<void> {
  const menu = page.getByRole("menu", { name: "Reacționează" });
  await expect(menu).toHaveCount(0); // the last one has finished closing
  const box = await target.boundingBox();
  if (!box) throw new Error("not visible");
  const finger = {
    pointerType: "touch",
    isPrimary: true,
    clientX: box.x + box.width / 2,
    clientY: box.y + box.height / 2,
  };
  await target.dispatchEvent("pointerdown", finger);
  await expect(menu).toBeVisible();
  await target.dispatchEvent("pointerup", finger);
}

/** The id of a card from before today. */
async function earlierCard(page: Page): Promise<string> {
  const today = ((await (await page.request.get("/api/v1/today")).json()) as { day: string }).day;
  const journal = (await (await page.request.get("/api/v1/journal")).json()) as {
    results: { id: string; day: string }[];
  };
  const card = journal.results.find((entry) => entry.day < today);
  if (!card) throw new Error("no card before today: make seed");
  return card.id;
}

/** Write in the box at the bottom of a card's page and send it. */
async function write(page: Page, text: string): Promise<void> {
  await page.getByRole("textbox", { name: "Comentariu" }).fill(text);
  await page.getByRole("button", { name: "Trimite" }).click();
  await expect(page.getByRole("textbox", { name: "Comentariu" })).toHaveValue("");
}

test("the crew comments on a card, replies, reacts and deletes", async ({ browser }) => {
  const stamp = Date.now().toString(36);
  const bravo = `Bravo ${stamp}`;
  const thanks = `Mersi ${stamp}`;

  const dan = await logIn(browser, "dan");
  const card = await earlierCard(dan);
  await dan.goto(`/crew/cards/${card}`);
  await write(dan, bravo);
  // The first: a reply to it quotes it further down.
  const his = dan.getByRole("article").filter({ hasText: bravo }).first();
  await expect(his).toBeVisible();
  await dan.goto("/crew"); // away from the card: what comes now is news to him

  const cristina = await logIn(browser, "cristina", devices["Desktop Chrome"]);
  await cristina.goto(`/crew/cards/${card}`);
  const hisThere = cristina.getByRole("article").filter({ hasText: bravo }).first();
  await hisThere.getByRole("button", { name: "Răspunde" }).click(); // a computer shows it
  await write(cristina, thanks);
  const hers = cristina.getByRole("article").filter({ hasText: thanks });
  await expect(hers).toBeVisible();

  await dan.reload();
  const link = dan.locator(`a[href="/crew/cards/${card}"]`);
  await expect(link).toContainText(/\bno[ui]\b/); // "1 nou", or more if others wrote too
  await link.click();
  await expect(dan.getByRole("article").filter({ hasText: thanks })).toBeVisible();
  await dan.goBack(); // seen: the mark goes
  await expect(link).toBeVisible();
  await expect(link).not.toContainText(/\bno[ui]\b/);
  await link.click();

  await hold(dan, his.getByText(bravo));
  await expect(dan.getByRole("menuitem", { name: "Răspunde" })).toBeVisible();
  await expect(dan.getByRole("menuitem", { name: "Șterge" })).toHaveCount(0); // it has a reply
  await dan.getByRole("menuitemradio", { name: FIRE }).click();
  await expect(his.getByRole("button", { name: `${FIRE}, de la tine` })).toBeVisible();

  await hers.getByRole("button", { name: "Reacționează" }).click();
  await cristina.getByRole("menuitem", { name: "Șterge" }).click();
  await expect(hers).toHaveCount(0);

  // Dan's page asks for the comments every 5 s: the reply goes, and his comment can go too.
  await expect(dan.getByRole("article").filter({ hasText: thanks })).toHaveCount(0, {
    timeout: 10_000,
  });
  await hold(dan, his.getByText(bravo));
  await dan.getByRole("menuitem", { name: "Șterge" }).click();
  await expect(his).toHaveCount(0);
});
