import { expect, test } from "@playwright/test";

test.describe("Einstufung", () => {
  test("stellt Sonden nacheinander und zeigt den Fortschritt", async ({ page }) => {
    await page.goto("/einstufung");

    await expect(page.getByText("Frage 1 von 6")).toBeVisible();
    await expect(page.getByRole("heading", { name: /gerolltes r/ })).toBeVisible();

    await page.getByRole("button", { name: "Р", exact: true }).click();
    await expect(page.getByText("Frage 2 von 6")).toBeVisible();
  });

  test("bricht nach zwei Fehlern in Folge ab und stuft ganz vorn ein", async ({ page }) => {
    await page.goto("/einstufung");

    await page.getByRole("button", { name: "П", exact: true }).click();
    await expect(page.getByText("Frage 2 von 6")).toBeVisible();
    await page.getByRole("button", { name: /wie ch in Bach/ }).click();

    await expect(page.getByRole("heading", { name: "Fertig!" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Mit Einheit 1 starten" })).toBeVisible();
  });

  test("führt bei lauter richtigen Antworten weiter nach hinten", async ({ page }) => {
    await page.goto("/einstufung");

    await page.getByRole("button", { name: "Р", exact: true }).click();
    await page.getByRole("button", { name: /wie j in Journal/ }).click();
    await page.getByRole("button", { name: "ъ", exact: true }).click();
    await page.getByRole("button", { name: /спаси́бо/ }).click();
    await page.getByRole("button", { name: /auf Wiedersehen/ }).click();
    await page.getByRole("button", { name: /тебя́/ }).click();

    await expect(page.getByRole("heading", { name: "Fertig!" })).toBeVisible();
    const link = page.getByRole("link", { name: /Mit Einheit \d+ starten/ });
    await expect(link).toBeVisible();
    await link.click();
    await expect(page).toHaveURL(/\/kurs\/\d+$/);
  });

  test("merkt sich das Ergebnis im Profil", async ({ page }) => {
    await page.goto("/einstufung");
    // Zwei Fehler in Folge beenden die Einstufung.
    await page.getByRole("button", { name: "П", exact: true }).click();
    await page.getByRole("button", { name: /wie ch in Bach/ }).click();
    await expect(page.getByRole("heading", { name: "Fertig!" })).toBeVisible();

    await page.goto("/profil");
    await expect(page.getByText(/Empfohlener Einstieg: Einheit \d+/)).toBeVisible();
  });
});
