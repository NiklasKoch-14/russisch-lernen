import { expect, test } from "@playwright/test";

test.describe("Profil", () => {
  test("schaltet die Umschrift ab und wieder an", async ({ page }) => {
    // Die Umschrift steht auf den Wortkacheln, nicht auf dem Regel-Bildschirm.
    await openExercises(page);
    await expect(page.getByText("po-rússki")).toBeVisible();

    await page.goto("/profil");
    const toggle = page.getByLabel("Umschrift anzeigen");
    await expect(toggle).toBeChecked();
    await toggle.uncheck();

    await openExercises(page);
    await expect(page.getByText("по-ру́сски")).toBeVisible();
    await expect(page.getByText("po-rússki")).toHaveCount(0);

    await page.goto("/profil");
    await page.getByLabel("Umschrift anzeigen").check();
    await openExercises(page);
    await expect(page.getByText("po-rússki")).toBeVisible();
  });

  test("hält das freie Gespräch vor Stufe 3 verschlossen", async ({ page }) => {
    await page.goto("/profil");
    await expect(page.getByText(/schaltet sich frei/)).toBeVisible();
    await expect(page.getByRole("link", { name: "Freies Gespräch öffnen" })).toHaveCount(0);
  });

  test("bietet die Einstufung an", async ({ page }) => {
    await page.goto("/profil");
    await page.getByRole("link", { name: "Einstufung starten" }).click();
    await expect(page).toHaveURL(/\/einstufung$/);
    await expect(page.getByText("Frage 1 von 6")).toBeVisible();
  });
});

/** Oeffnet Einheit 8 und ueberspringt den Regel-Bildschirm. */
async function openExercises(page: import("@playwright/test").Page) {
  await page.goto("/kurs/8");
  await page.getByRole("button", { name: "Los geht's" }).click();
}
