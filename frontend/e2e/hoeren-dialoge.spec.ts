import { expect, test } from "./fixtures";
import { stubServerAudio } from "./fixtures";

/** Setzt die Einstufung — davon hängt ab, welche Gespräche offen sind. */
async function place(page: import("@playwright/test").Page, unit: number): Promise<void> {
  const response = await page.request.patch("http://localhost:8001/api/profile", {
    data: { placement_unit: unit },
  });
  expect(response.ok()).toBeTruthy();
}

test.describe("Hörgespräche", () => {
  test("nennt die Einheit, die das erste Gespräch öffnet", async ({ page }) => {
    await place(page, 1);
    await page.goto("/hoeren");

    await expect(page.getByRole("heading", { name: "Noch kein Gespräch" })).toBeVisible();
    await expect(page.getByText(/Einheit 12/)).toBeVisible();
  });

  test("hört ein Gespräch, antwortet und liest nach", async ({ page }) => {
    await stubServerAudio(page, true);
    await place(page, 26);
    await page.goto("/hoeren");

    // Vor dem Hören: nur wer spricht, kein Text.
    await expect(page.getByText(/2 Sprecher · 3 Zeilen/)).toBeVisible();
    await expect(page.getByText("Sehr angenehm!")).toHaveCount(0);
    await expect(page.getByText("Worum ging es?")).toHaveCount(0);

    // Das Gespräch kommt als eine vorab geladene Spur, mit Balken für die Restzeit.
    await expect(page.getByRole("progressbar", { name: "Fortschritt des Gesprächs" })).toBeVisible();
    await page.getByRole("button", { name: /Abspielen/ }).click();
    await expect(page.getByText("Worum ging es?")).toBeVisible();

    await page.getByRole("button", { name: "Die beiden stellen sich einander vor." }).click();

    await expect(page.getByRole("heading", { name: "Zwei lernen sich kennen" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Zum Nachlesen" })).toBeVisible();
    await expect(page.getByText("Sehr angenehm!")).toBeVisible();

    await page.getByRole("button", { name: "Nächstes Gespräch" }).click();
    await expect(page.getByRole("button", { name: /Abspielen/ })).toBeVisible();
  });
});
