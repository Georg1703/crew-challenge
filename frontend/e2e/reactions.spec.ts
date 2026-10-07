import { expect, test, type Browser, type Page } from "@playwright/test";

// Reactions in Echipa against the real backend and the demo crew (`make seed`): Cristina checks
// in with a photo; Dan reacts from the quick row, changes it, Cristina sees it, Dan takes it back.
// Her check-in is undone at the end (its reactions go with it), so the test can run again.

const PASSWORD = "garden-flame-2026";
const WALK = "Plimbare (demo)";
const FIRE = "\u{1F525}";
const CLAP = "\u{1F44F}";
const PIXEL = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
); // a 1x1 PNG

async function logIn(browser: Browser, username: string): Promise<Page> {
  const page = await (await browser.newContext({ locale: "en-US" })).newPage();
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
  return page;
}

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

test("the crew reacts to a proof card, changes it and takes it back", async ({ browser }) => {
  const cristina = await logIn(browser, "cristina");
  const today = (await (await cristina.request.get("/api/v1/today")).json()) as {
    day: string;
    challenges: { id: string; title: string; state: string }[];
  };
  const walk = today.challenges.find((c) => c.title === WALK);
  if (!walk) throw new Error(`${WALK} is not running: make seed`);
  const undo = `/api/v1/challenges/${walk.id}/check-ins/${today.day}/last`;
  if (walk.state === "done") await send(cristina, "delete", undo); // left by a failed run

  try {
    await send(cristina, "post", `/api/v1/challenges/${walk.id}/check-ins`, { day: today.day });
    await cristina.goto("/");
    await cristina
      .locator("section")
      .filter({ has: cristina.getByRole("heading", { name: WALK }) })
      .last()
      .locator('input[accept="image/*"]')
      .setInputFiles({ name: "walk.png", mimeType: "image/png", buffer: PIXEL });
    await expect(
      cristina.getByRole("button", { name: "Poză. Atinge pentru a deschide" }),
    ).toBeVisible();

    const dan = await logIn(browser, "dan");
    await dan.goto("/crew");
    const card = dan.getByRole("article").filter({ hasText: "Cristina a bifat" }).first();
    await card.getByRole("button", { name: "Reacționează" }).click();
    await dan.getByRole("menuitemradio", { name: FIRE }).click();
    await expect(card.getByRole("button", { name: `${FIRE}, de la tine` })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await card.getByRole("button", { name: "Reacționează" }).click();
    await dan.getByRole("menuitemradio", { name: CLAP }).click();
    await expect(card.getByRole("button", { name: `${CLAP}, de la tine` })).toBeVisible();
    await expect(card.getByRole("button", { name: `${FIRE}, de la tine` })).toHaveCount(0);

    await cristina.goto("/crew");
    const hers = cristina.getByRole("article").filter({ hasText: "Cristina a bifat" }).first();
    await expect(hers.getByRole("button", { name: `${CLAP}, de la Dan` })).toBeVisible();

    await card.getByRole("button", { name: `${CLAP}, de la tine` }).click();
    await expect(card.getByRole("button", { name: `${CLAP}, de la tine` })).toHaveCount(0);
  } finally {
    await send(cristina, "delete", undo);
  }
});
