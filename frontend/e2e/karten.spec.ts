import { expect, test } from "./fixtures";

/** Setzt die Einstufung — davon hängt ab, welche Vokabeln im Stapel liegen. */
async function place(page: import("@playwright/test").Page, unit: number): Promise<void> {
  const response = await page.request.patch("http://localhost:8001/api/profile", {
    data: { placement_unit: unit },
  });
  expect(response.ok()).toBeTruthy();
}

test.describe("Karteikarten", () => {
  test("sagt es, wenn noch keine Wörter gelernt sind", async ({ page }) => {
    await place(page, 1);
    await page.goto("/karten");

    await expect(page.getByRole("heading", { name: "Noch keine Wörter" })).toBeVisible();
  });

  test("fragt ein Wort ab und meldet das Ergebnis", async ({ page }) => {
    await place(page, 13);
    await page.goto("/karten");

    await expect(page.getByText(/Karte 1 von/)).toBeVisible();
    await expect(page.getByText(/Wörter gelernt/)).toBeVisible();

    // Irgendeine Option — richtig oder falsch, beides muss zurückmelden.
    await page.locator("main button").filter({ hasText: /.+/ }).nth(4).click();
    await expect(page.getByRole("button", { name: "Weiter" })).toBeVisible();

    await page.getByRole("button", { name: "Weiter" }).click();
    await expect(page.getByText(/Karte 2 von/)).toBeVisible();
  });

  test("schaltet die Richtung um", async ({ page }) => {
    await place(page, 13);
    await page.goto("/karten");

    await page.getByRole("button", { name: "DE → RU" }).click();
    await expect(page.getByRole("button", { name: "DE → RU" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.getByText(/Karte 1 von/)).toBeVisible();
  });
});
