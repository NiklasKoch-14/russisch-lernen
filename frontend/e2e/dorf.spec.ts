import { expect, test } from "./fixtures";

test.describe("Dorf", () => {
  test("zeigt die Karte mit den Gebäuden und lässt eines anklicken", async ({ page }) => {
    await page.goto("/dorf");
    await expect(page.getByAltText("Das Dorf")).toBeVisible();

    const bar = page.getByRole("button", { name: /бар/ });
    await expect(bar).toBeVisible();
    await bar.click();

    await expect(page).toHaveURL(/\/dorf\/bar$/);
  });

  test("öffnet die Bar und stellt ihre Leute in den Raum", async ({ page }) => {
    await page.goto("/dorf");
    await page.getByRole("button", { name: /бар/ }).click();

    // Nicht irgendwo auf der Seite, sondern im Raumbild: eine Liste unter dem
    // Bild wuerde denselben Text zeigen und den Umbau unbemerkt lassen.
    const stage = page.getByTestId("place-stage");
    await expect(stage.getByRole("button", { name: /Пётр/ })).toBeVisible();
    await expect(stage.getByRole("button", { name: /На́дя/ })).toBeVisible();
  });

  test("spricht jemanden an und bringt das Gespräch bis zum Ende — auch bei lauter falschen Antworten", async ({
    page,
  }) => {
    await page.goto("/dorf");
    await page.getByRole("button", { name: /бар/ }).click();
    await page.getByRole("button", { name: /Пётр/ }).click();

    // Der Raum bleibt waehrend des Gespraechs stehen — das ist der Kern der
    // Ansicht; ohne ihn waere es wieder eine eigene Seite.
    await expect(page.getByTestId("place-stage")).toBeVisible();

    const progress = page.getByText(/Zug 1 von \d+/);
    await expect(progress).toBeVisible();
    // Die Gespraechsansicht stellt oben vor, mit wem man spricht.
    await expect(page.getByText("Пётр")).toBeVisible();
    await expect(page.getByText("Pjotr")).toBeVisible();

    // Wie viele Zuege es sind, sagt die Anzeige — nicht der Test. Pjotr hat
    // mehrere Szenen, und welche davon drankommt, haengt davon ab, was zuletzt
    // gespielt wurde; eine feste Zahl waere nur beim ersten Lauf richtig.
    const turnCount = Number(/von (\d+)/.exec((await progress.textContent()) ?? "")?.[1]);
    expect(turnCount).toBeGreaterThanOrEqual(2);

    // Jeden Zug der Szene bewusst falsch beantworten: die Zusicherung aus
    // der Fehlerbehandlung lautet, dass es trotzdem bis zum Ende geht — nach
    // einer falschen Antwort kommt derselbe Zug genau einmal wieder, danach
    // geht es weiter, unabhaengig vom zweiten Ausgang.
    for (let turn = 0; turn < turnCount; turn += 1) {
      await answerWrong(page);
      await page.getByRole("button", { name: "Nochmal" }).click();

      await answerWrong(page);
      await page.getByRole("button", { name: "Weiter" }).click();
    }

    await expect(page.getByRole("heading", { name: "Geschafft!" })).toBeVisible();
  });

  test("führt vom Sprachkurs in eine Einheit statt in ein Gespräch", async ({ page }) => {
    await page.goto("/dorf");
    await page.getByRole("button", { name: /шко́ла/ }).click();

    await page.getByRole("button", { name: /Einheit \d+ beginnen/ }).click();
    await expect(page).toHaveURL(/\/kurs\/\d+$/);
  });
});

/**
 * Waehlt alle Kacheln der aktuellen Aufgabe, statt die richtige Lösung zu
 * suchen, und prueft dann. Mit dabei sind auch die Distraktoren — die
 * Einsendung weicht damit garantiert von der Lösung ab, egal welcher Zug
 * gerade dran ist.
 */
async function answerWrong(page: import("@playwright/test").Page) {
  const idleTile = page.locator('main button[aria-pressed="false"]');
  while ((await idleTile.count()) > 0) {
    await idleTile.first().click();
  }
  await page.getByRole("button", { name: "Prüfen" }).click();
}
