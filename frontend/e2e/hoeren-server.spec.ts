import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { spokenTexts, stubServerAudio, stubSpeech } from "./fixtures";

/** Beantwortet die aktuelle Aufgabe irgendwie, damit der Test weiterkommt. */
async function answerCurrentExercise(page: Page) {
  const check = page.getByRole("button", { name: "Prüfen" });
  if (await check.isVisible().catch(() => false)) {
    await page.locator("main button[aria-pressed]").first().click();
    await check.click();
    return;
  }
  const grid = page.locator("main .grid");
  if (await grid.isVisible().catch(() => false)) {
    // Ein Raster, spaltenweise gefuellt: erst alle linken Karten, dann alle rechten.
    const cards = grid.locator("> button");
    const total = await cards.count();
    const count = total / 2;
    for (let index = 0; index < count; index += 1) {
      await cards.nth(index).click();
      await cards.nth(count + index).click();
    }
    return;
  }
  await page.locator("main button[aria-pressed]").first().click();
}

/** Spult bis zu der Aufgabe, die in Einheit 8 den Ton traegt (8-4). */
async function goToAudioExercise(page: Page) {
  await page.goto("/kurs/8");
  await page.getByRole("button", { name: "Los geht's" }).click();
  for (let step = 0; step < 3; step += 1) {
    await answerCurrentExercise(page);
    await page.getByRole("button", { name: "Weiter" }).click();
  }
}

test.describe("Ton vom Server", () => {
  test("holt den Satz beim Betreten vor und zeigt den deutschen Prompt nicht", async ({
    page,
  }) => {
    await stubServerAudio(page, true);
    await stubSpeech(page, ["de-DE"]);

    const abrufe: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("/api/audio?")) abrufe.push(request.url());
    });

    await goToAudioExercise(page);

    await expect(page.getByText("Hör zu.")).toBeVisible();
    await expect(page.getByText("Welche Endung passt zu я?")).toHaveCount(0);
    // Das Vorladen laeuft beim Betreten, ohne dass jemand geklickt hat.
    await expect.poll(() => abrufe.length).toBeGreaterThan(0);
  });

  test("braucht keine Browserstimme", async ({ page }) => {
    // Genau der Fall des Nutzers ohne installierte russische Stimme.
    await stubServerAudio(page, true);
    await stubSpeech(page, ["de-DE"]);

    await goToAudioExercise(page);
    await expect(page.getByRole("button", { name: "Anhören", exact: true })).toBeVisible();
  });
});

test.describe("Server stumm", () => {
  test("fällt auf die Browserstimme zurück", async ({ page }) => {
    await stubServerAudio(page, false);
    await stubSpeech(page, ["ru-RU"]);

    await goToAudioExercise(page);
    await page.getByRole("button", { name: "Anhören", exact: true }).click();

    await expect.poll(async () => (await spokenTexts(page)).length).toBeGreaterThan(0);
  });

  test("zeigt die Textfassung, wenn auch keine Browserstimme da ist", async ({ page }) => {
    await stubServerAudio(page, false);
    await stubSpeech(page, ["de-DE"]);

    await goToAudioExercise(page);
    await expect(page.getByText("Welche Endung passt zu я?")).toBeVisible();
    await expect(page.getByRole("button", { name: /[Aa]nhören/ })).toHaveCount(0);
  });
});
