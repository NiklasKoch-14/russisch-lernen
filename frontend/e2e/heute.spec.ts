import { expect, test } from "./fixtures";

test.describe("Heute", () => {
  test("ist die Startseite und führt mit einem Knopf zum nächsten Schritt", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("link", { name: "Heute" })).toHaveAttribute("aria-current", "page");
    const plan = page.getByRole("list", { name: "Heute dran" });
    await expect(plan).toBeVisible();
    await expect(plan.locator('[aria-current="step"]')).toHaveCount(1);

    // Welcher Schritt vorn steht, hängt davon ab, was frühere Tests in dieser
    // Datenbank getan haben — geprüft wird, dass der Knopf ihn auch öffnet.
    const primary = page.getByRole("link", { name: /^(Los|Weiter): .+ · ca\. \d+ Min\.$/ });
    await expect(primary).toHaveCount(1);
    const target = await primary.getAttribute("href");
    await primary.click();
    await expect(page).not.toHaveURL(/\/$/);
    expect(target).not.toBe("/");
  });

  test("führt immer auch zur Liste aller Einheiten", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Alle Einheiten" }).click();
    await expect(page).toHaveURL(/\/kurs$/);
    await expect(page.getByRole("heading", { name: "Schrift & Klang" })).toBeVisible();
  });

  test("startet eine vorgeschlagene Dorfszene direkt", async ({ page }) => {
    await page.goto("/dorf/kafe?szene=kafe-02");
    await expect(page).toHaveURL(/\/dorf\/kafe\/szene\/kafe-02\?seed=/);
    await expect(page.getByTestId("dialog-card")).toBeVisible();
  });
});
