import { expect, test, type Browser, type Page } from "@playwright/test";

// Echipa as the crew's journal, against the real backend and the demo crew from `make seed`:
// Cristina checks in and her ring fills; she adds a photo; Dan sees a new-proof count on her
// ring, opens her page and her photo, and the count is gone. Her check-in is undone at the end
// (undo takes its proofs), so the test can run again the same day. Demo accounts use Romanian.

const PASSWORD = "garden-flame-2026";
const WALK = "Plimbare (demo)";
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

/** The API as the SPA calls it: with the CSRF token. */
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

/** "azi 1 din 3" from a ring's label. */
function doneOf(label: string | null): number {
  return Number(/azi (\d+) din/.exec(label ?? "")?.[1] ?? -1);
}

test("a check-in fills the ring, a new photo shows on it, and the member page opens it", async ({
  browser,
}) => {
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
    await cristina.goto("/crew");
    const mine = cristina
      .getByRole("list", { name: "Azi în echipă" })
      .getByRole("link", { name: /^Cristina: azi/ });
    const before = doneOf(await mine.getAttribute("aria-label"));

    await send(cristina, "post", `/api/v1/challenges/${walk.id}/check-ins`, { day: today.day });
    await cristina.reload();
    await expect.poll(async () => doneOf(await mine.getAttribute("aria-label"))).toBe(before + 1);
    await expect(cristina.getByText("Cristina a bifat").first()).toBeVisible();

    await cristina.goto("/");
    const card = cristina
      .locator("section")
      .filter({ has: cristina.getByRole("heading", { name: WALK }) })
      .last();
    await card
      .locator('input[type="file"]')
      .setInputFiles({ name: "walk.png", mimeType: "image/png", buffer: PIXEL });
    await expect(
      card.getByRole("button", { name: "Poză. Atinge pentru a deschide" }),
    ).toBeVisible();

    const dan = await logIn(browser, "dan");
    await dan.goto("/crew");
    const hers = dan
      .getByRole("list", { name: "Azi în echipă" })
      .getByRole("link", { name: /^Cristina: azi/ });
    await expect(hers).toHaveAccessibleName(/dovad|dovezi/);
    await hers.click();

    await expect(dan.getByRole("heading", { level: 1, name: "Cristina" })).toBeVisible();
    const proofs = dan.getByRole("region", { name: "Dovezi" });
    await proofs.getByRole("button", { name: "Poză de la Cristina" }).first().click();
    await expect(dan.getByRole("dialog", { name: "Dovezi" })).toBeVisible();
    await dan.keyboard.press("Escape");

    await dan.goto("/crew");
    await expect(hers).toBeVisible();
    await expect(hers).not.toHaveAccessibleName(/dovad|dovezi/);
  } finally {
    await send(cristina, "delete", undo);
  }
});
