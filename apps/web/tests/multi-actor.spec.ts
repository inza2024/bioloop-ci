import { expect, test } from "@playwright/test";


test("parcours multi-acteurs attribué du producteur au contrôle P4", async ({ page }) => {
  await page.goto("/");

  const roleSelector = page.getByTestId("demo-role-selector");
  await expect(roleSelector).toBeVisible();
  await expect(page.getByText("Mode démonstration", { exact: true })).toBeVisible();
  await expect(page.getByText(/ne remplace ni connexion, ni MFA/)).toBeVisible();

  await roleSelector.selectOption("USER-PROD-001");
  await page.getByTestId("quantity-input").fill("1337");
  await page.getByRole("button", { name: "Enregistrer et chercher une unité" }).click();
  const declarationRecap = page.getByTestId("declaration-recap");
  await expect(declarationRecap).toContainText("1 337 kg");
  const declarationId = (await declarationRecap.textContent())?.match(/DECL-[A-F0-9]{12}/)?.[0];
  expect(declarationId).toBeTruthy();
  await page.getByTestId("generate-proposal").click();
  await expect(page.getByTestId("proposal-results")).toBeVisible();

  await roleSelector.selectOption("USER-LOG-001");
  const collection = page.locator(`[data-declaration-id="${declarationId}"]`);
  await expect(collection).toBeVisible();
  await expect(collection).toContainText("Ce n’est pas un itinéraire routier");
  await collection.getByTestId("logistics-evidence").setInputFiles({
    name: "bon-pesee-e2e.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\nBioLoop Playwright evidence\n%%EOF\n"),
  });
  await collection.getByTestId("logistics-weight").fill("1188");
  await collection.getByRole("button", { name: "Confirmer collecte, pesée et lot" }).click();
  await expect(collection).toContainText("collected");

  await roleSelector.selectOption("USER-UNIT-001");
  const incomingLot = page.locator(`[data-declaration-id="${declarationId}"]`);
  await expect(incomingLot).toBeVisible();
  await expect(page.getByText("Projection déterministe", { exact: false })).toBeVisible();
  await incomingLot.getByTestId("unit-decision").click();
  await expect(incomingLot).toContainText("Décision enregistrée : accepted");

  await roleSelector.selectOption("USER-CONTROL-001");
  const pendingControl = page.locator(`[data-declaration-id="${declarationId}"]`);
  await expect(pendingControl).toBeVisible();
  await pendingControl.getByTestId("controller-verify").click();
  await expect(pendingControl).toHaveCount(0);

  await roleSelector.selectOption("USER-PROD-001");
  await expect(page.getByText("lot.decision_recorded", { exact: true }).first()).toBeVisible();

  await roleSelector.selectOption("USER-CLIENT-001");
  await expect(page.getByText("0 produit inventé", { exact: true })).toBeVisible();
  await expect(page.getByText("Aucune disponibilité qualifiée à afficher")).toBeVisible();
});
