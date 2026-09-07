import { expect, test } from "./fixtures";

test.describe("Kurs", () => {
  test("zeigt die Stufen mit ihren Einheiten", async ({ page }) => {
    await page.goto("/kurs");

    await expect(page.getByRole("heading", { name: "Schrift & Klang" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Erste Sätze" })).toBeVisible();

    await expect(page.getByRole("link", { name: /Buchstaben, die täuschen/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /Meine Familie/ })).toBeVisible();
  });

  test("öffnet eine Einheit mit Regel vor den Aufgaben", async ({ page }) => {
    await page.goto("/kurs");
    await page.getByRole("link", { name: /Sprichst du Russisch\?/ }).click();

    await expect(page).toHaveURL(/\/kurs\/8$/);
    await expect(page.getByRole("heading", { name: "Sprichst du Russisch?" })).toBeVisible();
    await expect(page.getByText("Die Endung sagt, wer spricht")).toBeVisible();
    await expect(page.getByText(/говорю́/)).toBeVisible();

    await page.getByRole("button", { name: "Los geht's" }).click();
    await expect(page.getByText(/Aufgabe 1 von \d+/)).toBeVisible();
  });

  test("löst eine Wortformaufgabe richtig und meldet Erfolg", async ({ page }) => {
    await page.goto("/kurs/8");
    await page.getByRole("button", { name: "Los geht's" }).click();

    // Bis zur ersten Formauswahl vorspulen (Aufgabe 8-4).
    await solveThroughTo(page, "Welche Endung passt zu я?");

    // я ... по-ру́сски -> говорю́
    await page.getByRole("button", { name: /^говорю́/ }).click();
    await expect(page.getByTestId("feedback")).toContainText("Richtig!");
  });

  test("erklärt eine falsche Wortform statt sie nur abzulehnen", async ({ page }) => {
    await page.goto("/kurs/8");
    await page.getByRole("button", { name: "Los geht's" }).click();
    await solveThroughTo(page, "Welche Endung passt zu я?");

    await page.getByRole("button", { name: /^говори́т/ }).first().click();

    const feedback = page.getByTestId("feedback");
    await expect(feedback).toContainText("Nicht ganz.");
    await expect(feedback).toContainText("Richtig ist:");
    await expect(feedback).toContainText("говорю́");
  });

  test("merkt sich den Fortschritt nach dem Neuladen", async ({ page }) => {
    await page.goto("/kurs/5");
    await page.getByRole("button", { name: "Los geht's" }).click();
    await answerCurrentExercise(page);
    await page.getByRole("button", { name: "Weiter" }).click();

    await page.goto("/kurs");
    const link = page.getByRole("link", { name: /Hallo und tschüss/ });
    await expect(link).toHaveAttribute("aria-label", /angefangen|abgeschlossen/);
  });
});

/** Beantwortet die aktuelle Aufgabe irgendwie, damit der Test weiterkommt. */
async function answerCurrentExercise(page: import("@playwright/test").Page) {
  const check = page.getByRole("button", { name: "Prüfen" });
  if (await check.isVisible().catch(() => false)) {
    // Satzbau: irgendeine Kachel wählen, dann prüfen.
    await page.locator("main button[aria-pressed]").first().click();
    await check.click();
    return;
  }
  // Zuordnen: linke Spalte mit rechter Spalte der Reihe nach verbinden.
  const grid = page.locator("main .grid");
  if (await grid.isVisible().catch(() => false)) {
    // Ein Raster, spaltenweise gefuellt: erst alle linken Karten, dann alle rechten.
    const cards = grid.locator("> button");
    const total = await cards.count();
    const count = total / 2;
    for (let i = 0; i < count; i += 1) {
      await cards.nth(i).click();
      await cards.nth(count + i).click();
    }
    return;
  }
  // Auswahlaufgabe: erste Option.
  const pressable = page.locator("main button[aria-pressed]");
  if ((await pressable.count()) > 0) {
    await pressable.first().click();
    return;
  }
  // Bedeutung waehlen: schlichte Knoepfe ohne aria-pressed.
  await page.getByRole("button").filter({ hasNotText: "Weiter" }).first().click();
}

/** Spult durch Aufgaben, bis die gesuchte Aufgabenstellung erscheint. */
async function solveThroughTo(page: import("@playwright/test").Page, promptFragment: string) {
  for (let step = 0; step < 12; step += 1) {
    if (await page.getByText(promptFragment).isVisible().catch(() => false)) return;
    await answerCurrentExercise(page);
    await page.getByRole("button", { name: "Weiter" }).click();
  }
  throw new Error(`Aufgabe mit "${promptFragment}" nicht erreicht`);
}
