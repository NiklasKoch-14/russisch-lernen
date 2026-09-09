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

    await useMode(page, "tiles");

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

  test("kommt ohne Scrollen aus — die Wege zurück sind immer sichtbar", async ({ page }) => {
    // Auf einem gewoehnlichen Fenster soll man ein Haus betreten und wieder
    // verlassen koennen, ohne die Seite zu bewegen.
    for (const path of ["/dorf", "/dorf/bar", "/dorf/magazin", "/dorf/shkola"]) {
      await page.goto(path);
      await expect(page.getByTestId(path === "/dorf" ? "village-map" : "place-stage")).toBeVisible();

      const scrolls = await page.evaluate(
        () => document.documentElement.scrollHeight > window.innerHeight + 1,
      );
      expect(scrolls, `${path} laesst sich scrollen`).toBe(false);
    }

    await page.goto("/dorf/bar");
    const back = page.getByRole("button", { name: "Zurück ins Dorf" });
    await expect(back).toBeInViewport();
  });

  test("lässt die Antwort tippen und benennt den Fehler", async ({ page }) => {
    // Bewusst schmaler als der Standard: die Tastatur steht in der Dialogkarte,
    // und feste Tastenbreiten liefen dort bei kleineren Fenstern aus dem Rahmen.
    await page.setViewportSize({ width: 1024, height: 700 });
    await page.goto("/dorf");
    await page.getByRole("button", { name: /бар/ }).click();
    await page.getByRole("button", { name: /Пётр/ }).click();
    await useMode(page, "typing");

    // Die Bildschirmtastatur schreibt ins Feld — auf einer deutschen Tastatur
    // gibt es sonst keinen Weg zu kyrillischen Buchstaben.
    const field = page.getByLabel("Deine Antwort auf Russisch");
    await expect(field).toBeVisible();

    // So viele Unsinnswoerter wie gesucht sind: bei falscher Wortzahl meldet
    // die Pruefung nur die Laenge und kommt gar nicht bis zum ersten Wort.
    const wanted = (await page.getByText(/^(ein Wort|\d+ Wörter)$/).textContent()) ?? "";
    const count = wanted === "ein Wort" ? 1 : Number(/\d+/.exec(wanted)?.[0]);
    for (let word = 0; word < count; word += 1) {
      if (word > 0) await page.getByRole("button", { name: "Leerzeichen" }).click();
      for (const letter of ["к", "в", "а"]) {
        await page.getByRole("button", { name: letter, exact: true }).click();
      }
    }
    await expect(field).toHaveValue(Array(count).fill("ква").join(" "));

    const keysOverflow = await page
      .getByTestId("cyrillic-keyboard")
      .evaluate((keyboard) =>
        [...keyboard.children].some((row) => row.scrollWidth > row.clientWidth),
      );
    expect(keysOverflow, "Die Tastatur passt nicht in die Karte").toBe(false);

    await page.getByRole("button", { name: "Prüfen" }).click();

    // Nicht nur „falsch": die Rueckmeldung sagt, was mit dem Wort nicht stimmt,
    // und markiert es in der eigenen Antwort.
    await expect(page.getByTestId("turn-feedback")).toContainText("Nicht ganz.");
    await expect(page.getByTestId("turn-feedback")).toContainText("kommt im Kurs nicht vor");
    const marked = page.getByTestId("typed-answer").locator("span").first();
    await expect(marked).toHaveClass(/rose/);
  });

  test("führt vom Sprachkurs in eine Einheit statt in ein Gespräch", async ({ page }) => {
    await page.goto("/dorf");
    await page.getByRole("button", { name: /шко́ла/ }).click();

    await page.getByRole("button", { name: /Einheit \d+ beginnen/ }).click();
    await expect(page).toHaveURL(/\/kurs\/\d+$/);
  });
});

/**
 * Stellt die Aufgabenform der Szene ein, statt sich auf die Vorgabe zu
 * verlassen: der Schalter merkt sich die Wahl im Profil, und die Tests teilen
 * sich eine Datenbank — welcher Modus gerade gilt, haengt sonst davon ab, was
 * vorher lief.
 */
async function useMode(page: import("@playwright/test").Page, mode: "tiles" | "typing") {
  // Erst abwarten, dass die Aufgabe ueberhaupt dasteht: vorher gibt es den
  // Schalter nicht, und "nicht da" liesse sich nicht von "schon im richtigen
  // Modus" unterscheiden.
  await expect(page.getByRole("button", { name: "Prüfen" })).toBeVisible();

  const wanted = page.getByRole("button", {
    name: mode === "tiles" ? "lieber Kacheln" : "lieber tippen",
  });
  if ((await wanted.count()) > 0) await wanted.click();

  // Warten, bis die neue Aufgabenform wirklich dasteht: der Wechsel holt den
  // Zug neu, und beide Formen haben einen Knopf "Prüfen" — wer zu frueh
  // weitermacht, bedient die alte Aufgabe.
  await expect(
    mode === "tiles"
      ? page.locator('main button[aria-pressed]').first()
      : page.getByLabel("Deine Antwort auf Russisch"),
  ).toBeVisible();
}

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
