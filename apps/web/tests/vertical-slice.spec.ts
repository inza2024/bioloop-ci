import { expect, test } from "@playwright/test";

test("un utilisateur crée une déclaration et obtient trois scénarios et une collecte", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /Du gisement déclaré/ })).toBeVisible();
  await expect(page.getByTestId("producer-list").locator("article")).toHaveCount(8);
  await expect(page.getByTestId("unit-list").locator("article")).toHaveCount(2);

  await page.getByTestId("quantity-input").fill("1500");
  await page.getByRole("button", { name: "Enregistrer et chercher une unité" }).click();

  await expect(page.getByTestId("declaration-recap")).toContainText("1 500 kg");
  await page.getByTestId("generate-proposal").click();

  const results = page.getByTestId("proposal-results");
  await expect(results).toBeVisible();
  await expect(results.getByText("SCÉNARIO BAS")).toBeVisible();
  await expect(results.getByText("SCÉNARIO CENTRAL")).toBeVisible();
  await expect(results.getByText("SCÉNARIO HAUT")).toBeVisible();
  await expect(results.getByText(/Ces résultats ne sont ni un rendement biogaz/)).toBeVisible();
  await expect(results.getByText("Validation humaine requise")).toBeVisible();
});
