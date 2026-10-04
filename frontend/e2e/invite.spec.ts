import { expect, test, type Browser, type Page } from "@playwright/test";

// The invite flow end to end against the real backend and the demo crews from `make seed`:
// Demo Crew (ana is the admin, bogdan a member) and Echipa Eva (eva is the admin).
// Anonymous pages follow the browser (English). After login the UI switches to the account's
// saved language, Romanian for demo and new accounts.

const PASSWORD = "garden-flame-2026";

function unique(prefix: string): string {
  return `${prefix}${Date.now().toString(36)}${Math.floor(Math.random() * 1000)}`;
}

async function newPage(browser: Browser): Promise<Page> {
  return (await browser.newContext({ locale: "en-US" })).newPage();
}

async function logIn(page: Page, username: string) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

/** As a logged-in admin: open Crew, open the invite sheet, return the invite's path. */
async function inviteLink(page: Page): Promise<string> {
  await page.goto("/crew");
  await page.getByRole("button", { name: "Invită pe cineva" }).click();
  const sheet = page.getByRole("dialog", { name: "Invită pe cineva" });
  await expect(sheet.getByRole("img", { name: "Cod QR pentru invitație" })).toBeVisible();
  const url = await sheet.getByLabel("Linkul de invitație").inputValue();
  expect(url).toMatch(/\/join\/[a-z0-9]+$/);
  await sheet.getByRole("button", { name: "Închide" }).click();
  return new URL(url).pathname;
}

/** As an anonymous visitor on an invite: accept and create an account. */
async function createAccount(page: Page, path: string, name: string, username: string) {
  await page.goto(path);
  await page.getByRole("button", { name: "Accept the invite" }).click();
  await page.getByLabel("What should we call you?").fill(name);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Join the crew" }).click();
  await expect(page).toHaveURL(/\/welcome$/);
}

test("a new person joins with an invite link, and the link then stops working", async ({
  page,
  browser,
}) => {
  await logIn(page, "ana");
  const path = await inviteLink(page);
  const code = path.split("/").pop() ?? "";
  await expect(page.getByText(`Link ${code.toUpperCase()}`)).toBeVisible();

  const guest = await newPage(browser);
  await guest.goto(path);
  await expect(guest.getByRole("heading", { name: "Join Demo Crew" })).toBeVisible();
  await expect(guest.getByText("Ana invited you.")).toBeVisible();

  const name = unique("Lena");
  await createAccount(guest, path, name, unique("lena"));
  await expect(guest.getByRole("heading", { name: `Bun venit, ${name}` })).toBeVisible();
  await guest.getByRole("button", { name: "Începe" }).click();
  await expect(guest.getByRole("heading", { name: `Bună, ${name}` })).toBeVisible();

  // The admin sees the new member, and the invite is no longer pending.
  await page.reload();
  await expect(page.getByRole("list", { name: "Membrii echipei" }).getByText(name)).toBeVisible();
  await expect(page.getByText(`Link ${code.toUpperCase()}`)).toHaveCount(0);

  // The same link a second time.
  const late = await newPage(browser);
  await late.goto(path);
  await expect(late.getByRole("heading", { name: "This invite no longer works" })).toBeVisible();
  await expect(late.getByText(/already used/)).toBeVisible();
});

test("an admin cancels an invite and its link stops working", async ({ page, browser }) => {
  await logIn(page, "ana");
  const path = await inviteLink(page);
  const code = path.split("/").pop() ?? "";

  const row = page.getByRole("listitem").filter({ hasText: `Link ${code.toUpperCase()}` });
  await row.getByRole("button", { name: "Anulează" }).click();
  await page
    .getByRole("dialog", { name: "Anulezi invitația?" })
    .getByRole("button", { name: "Anulează invitația" })
    .click();
  await expect(page.getByText("Invitație anulată")).toBeVisible();
  await expect(row).toHaveCount(0);

  const guest = await newPage(browser);
  await guest.goto(path);
  await expect(guest.getByRole("heading", { name: "This invite no longer works" })).toBeVisible();
  await expect(guest.getByText(/doesn't exist or was cancelled/)).toBeVisible();
});

test("someone with an account in another crew joins with it", async ({ page, browser }) => {
  // A person who belongs to Eva's crew.
  const eva = await newPage(browser);
  await logIn(eva, "eva");
  const evaPath = await inviteLink(eva);
  const name = unique("Mara");
  const username = unique("mara");
  await createAccount(await newPage(browser), evaPath, name, username);

  // Ana invites them to Demo Crew; they log in from the invite and join with their account.
  await logIn(page, "ana");
  const path = await inviteLink(page);
  const person = await newPage(browser);
  await person.goto(path);
  await person.getByRole("button", { name: "I already have an account" }).click();
  await expect(person).toHaveURL(/\/login\?next=/);
  await person.getByLabel("Username").fill(username);
  await person.getByLabel("Password").fill(PASSWORD);
  await person.getByRole("button", { name: "Log in" }).click();

  await expect(
    person.getByRole("heading", { name: "Intră în Demo Crew cu contul tău" }),
  ).toBeVisible();
  await expect(person.getByLabel("Cum să-ți spunem?")).toHaveValue(name);
  await person.getByRole("button", { name: "Intră în echipă" }).click();
  await expect(person).toHaveURL(/\/welcome$/);
  await expect(person.getByText("Așa merge totul în Demo Crew:")).toBeVisible();

  await page.reload();
  await expect(page.getByRole("list", { name: "Membrii echipei" }).getByText(name)).toBeVisible();
});

test("a taken username shows under the username field", async ({ page, browser }) => {
  await logIn(page, "ana");
  const path = await inviteLink(page);

  const guest = await newPage(browser);
  await guest.goto(path);
  await guest.getByRole("button", { name: "Accept the invite" }).click();
  await guest.getByLabel("What should we call you?").fill(unique("Ion"));
  await guest.getByLabel("Username").fill("ana");
  await guest.getByLabel("Password").fill(PASSWORD);
  await guest.getByRole("button", { name: "Join the crew" }).click();
  await expect(guest.getByLabel("Username")).toHaveAccessibleDescription(/taken/i);
});

test("members who are not admins cannot invite", async ({ page }) => {
  await logIn(page, "bogdan");
  await page.goto("/crew");
  await expect(page.getByRole("list", { name: "Membrii echipei" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Invită pe cineva" })).toHaveCount(0);
});
