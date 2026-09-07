import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { spokenTexts, stubSpeech } from "./fixtures";

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
    const left = grid.locator("> div").first().locator("button");
    const right = grid.locator("> div").last().locator("button");
    const count = await left.count();
    for (let index = 0; index < count; index += 1) {
      await left.nth(index).click();
      await right.nth(index).click();
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

test.describe("Hör-Aufgaben mit russischer Stimme", () => {
  test.beforeEach(async ({ page }) => {
    await stubSpeech(page, ["ru-RU"]);
  });

  test("spielt den Satz vor und zeigt den deutschen Prompt nicht", async ({ page }) => {
    await goToAudioExercise(page);

    await expect(page.getByText("Hör zu.")).toBeVisible();
    await expect(page.getByText("Welche Endung passt zu я?")).toHaveCount(0);

    // Der Satz wird beim Betreten einmal automatisch gesprochen ...
    await expect.poll(async () => (await spokenTexts(page)).length).toBeGreaterThan(0);

    // ... und zwar ohne die Betonungszeichen aus dem Content.
    const spoken = await spokenTexts(page);
    expect(spoken.join(" ")).not.toContain("́");
  });

  test("spricht auf Knopfdruck noch einmal, auch langsam", async ({ page }) => {
    await goToAudioExercise(page);
    const before = (await spokenTexts(page)).length;

    await page.getByRole("button", { name: "Anhören", exact: true }).click();
    await page.getByRole("button", { name: "Langsam anhören" }).click();

    await expect
      .poll(async () => (await spokenTexts(page)).length)
      .toBeGreaterThan(before + 1);
  });
});

test.describe("Ohne russische Stimme", () => {
  test.beforeEach(async ({ page }) => {
    await stubSpeech(page, ["de-DE"]);
  });

  test("fällt auf den deutschen Prompt zurück und bleibt lösbar", async ({ page }) => {
    await goToAudioExercise(page);

    await expect(page.getByText("Welche Endung passt zu я?")).toBeVisible();
    await expect(page.getByRole("button", { name: /[Aa]nhören/ })).toHaveCount(0);

    await page.getByRole("button", { name: /^говорю́/ }).click();
    await expect(page.getByTestId("feedback")).toContainText("Richtig!");
  });
});
