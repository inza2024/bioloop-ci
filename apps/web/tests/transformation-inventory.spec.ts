import { expect, test } from "@playwright/test";


test("transformation mesurée, libération P4, disponibilité et réservation sur desktop et mobile", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");

  const roleSelector = page.getByTestId("demo-role-selector");
  await roleSelector.selectOption("USER-PROD-001");
  await page.getByTestId("quantity-input").fill("1642");
  await page.getByRole("button", { name: "Enregistrer et chercher une unité" }).click();
  const declarationRecap = page.getByTestId("declaration-recap");
  const declarationId = (await declarationRecap.textContent())?.match(/DECL-[A-F0-9]{12}/)?.[0];
  expect(declarationId).toBeTruthy();
  await page.getByTestId("generate-proposal").click();
  await expect(page.getByTestId("proposal-results")).toBeVisible();

  await roleSelector.selectOption("USER-LOG-001");
  const collection = page.locator(`[data-declaration-id="${declarationId}"]`);
  await expect(collection).toBeVisible();
  await collection.getByTestId("logistics-evidence").setInputFiles({
    name: "bon-transformation-e2e.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\nBioLoop transformation E2E\n%%EOF\n"),
  });
  await collection.getByTestId("logistics-weight").fill("1400");
  await collection.getByRole("button", { name: "Confirmer collecte, pesée et lot" }).click();
  await expect(collection).toContainText("collected");

  await roleSelector.selectOption("USER-UNIT-001");
  const incomingLot = page.locator(`[data-declaration-id="${declarationId}"]`);
  await expect(incomingLot).toBeVisible();
  const lotId = (await incomingLot.textContent())?.match(/LOT-[A-F0-9]{12}/)?.[0];
  expect(lotId).toBeTruthy();
  await incomingLot.getByTestId("unit-decision").click();
  await expect(incomingLot).toContainText("accepted");

  const acceptedLot = page.locator(`[data-lot-id="${lotId}"]`);
  await expect(acceptedLot).toBeVisible();
  await acceptedLot.getByTestId("create-transformation").click();
  const transformation = page.locator("[data-transformation-id]").first();
  await expect(transformation).toContainText("aucune URI illustrative n’est convertie");
  await transformation.getByTestId("output-category").selectOption("raw_digestate");
  await transformation.getByTestId("output-quantity").fill("900");
  await transformation.getByTestId("create-product-output").click();
  await expect(page.getByTestId("transformation-workspace")).toContainText("Digestat brut — usage à qualifier");
  await expect(page.getByTestId("transformation-workspace")).toContainText("quarantine");

  await roleSelector.selectOption("USER-CONTROL-001");
  const qualityWorkspace = page.getByTestId("quality-workspace");
  const product = qualityWorkspace.locator("[data-product-id]").first();
  await expect(product).toContainText("quarantine");
  const productId = await product.getAttribute("data-product-id");
  expect(productId).toBeTruthy();
  await product.getByTestId("add-quality-test").click();
  await expect(qualityWorkspace.locator(`[data-product-id="${productId}"]`)).toContainText("pending_analysis");
  await qualityWorkspace.locator(`[data-product-id="${productId}"]`).getByTestId("release-product").click();
  await expect(qualityWorkspace.locator(`[data-product-id="${productId}"]`)).toContainText("released");

  await roleSelector.selectOption("USER-CLIENT-001");
  const clientWorkspace = page.getByTestId("client-product-workspace");
  const availableProduct = clientWorkspace.locator(`[data-product-id="${productId}"]`);
  await expect(availableProduct).toContainText("Digestat brut — usage à qualifier");
  await expect(availableProduct).toContainText("900 kg");
  await clientWorkspace.getByTestId("client-location-filter").fill("Anyama");
  await clientWorkspace.getByTestId("client-proof-filter").selectOption("P4");
  await expect(availableProduct).toBeVisible();
  await clientWorkspace.getByTestId("reservation-quantity").fill("25");
  await availableProduct.getByTestId("reserve-product").click();
  const reservation = clientWorkspace.locator(".reservation-list article").first();
  await expect(reservation).toContainText("25 kg · active");
  await availableProduct.getByRole("button", { name: "Voir la chaîne de provenance" }).click();
  await expect(clientWorkspace.getByTestId("provenance-chain")).toContainText("déclaration DECL-");
  await expect(clientWorkspace.getByTestId("provenance-chain")).toContainText("réservation RES-");
  await reservation.getByTestId("cancel-reservation").click();
  await expect(clientWorkspace.locator(".reservation-list article").first()).toContainText("cancelled");

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(clientWorkspace).toBeVisible();
  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  const offenders = horizontalOverflow > 1
    ? await page.locator("body *").evaluateAll((elements) => elements.flatMap((element) => {
      const box = element.getBoundingClientRect();
      return box.right > document.documentElement.clientWidth + 1 || box.left < -1
        ? [`${element.tagName.toLowerCase()}.${element.className}: ${Math.round(box.left)}..${Math.round(box.right)}`]
        : [];
    }).slice(0, 12))
    : [];
  expect(horizontalOverflow, offenders.join(" | ")).toBeLessThanOrEqual(1);
});
