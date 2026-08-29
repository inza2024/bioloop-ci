import { expect, test } from "@playwright/test";

test("parcours complet P1 vers P2, P3, lot, décision et recalcul", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("quantity-input").fill("1500");
  await page.getByRole("button", { name: "Enregistrer et chercher une unité" }).click();
  await expect(page.getByTestId("declaration-recap")).toContainText("1 500 kg");
  await page.getByTestId("generate-proposal").click();
  await expect(page.getByTestId("proposal-results")).toBeVisible();

  const workflow = page.getByTestId("traceability-workflow");
  await expect(workflow).toBeVisible();
  await page.getByTestId("evidence-file").setInputFiles({
    name: "bon-pesee-demo.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\nBioLoop Playwright evidence\n%%EOF\n"),
  });
  await page.getByTestId("upload-evidence").click();
  await expect(page.getByTestId("evidence-summary")).toContainText("bon-pesee-demo.pdf");

  await page.getByTestId("measured-quantity").fill("1200");
  await page.getByTestId("record-measurement").click();
  await expect(page.getByTestId("measurement-summary")).toContainText("1 200,00 kg");

  await page.getByTestId("create-lot").click();
  await expect(page.getByTestId("lot-summary")).toContainText("1 200,00 kg");

  await page.getByTestId("record-decision").click();
  await expect(page.getByTestId("decision-summary")).toContainText("Lot accepté");
  await expect(page.getByTestId("decision-summary")).toContainText("non authentifiée");

  const comparison = page.getByTestId("mass-comparison");
  await expect(comparison).toContainText("1 500,00 kg");
  await expect(comparison).toContainText("1 200,00 kg");
  await page.getByTestId("recalculate-estimate").click();

  const recalculation = page.getByTestId("recalculation-results");
  await expect(recalculation).toBeVisible();
  await expect(recalculation.getByText("L’entrée est P3 ; les résultats restent P0.")).toBeVisible();
  await expect(recalculation.getByText("SCÉNARIO BAS")).toBeVisible();
  await expect(recalculation.getByText("SCÉNARIO CENTRAL")).toBeVisible();
  await expect(recalculation.getByText("SCÉNARIO HAUT")).toBeVisible();

  const timeline = page.getByTestId("timeline");
  await expect(timeline).toContainText("evidence.created");
  await expect(timeline).toContainText("measurement.recorded");
  await expect(timeline).toContainText("lot.created");
  await expect(timeline).toContainText("lot.accepted");
  await expect(timeline).toContainText("estimate.recalculated_from_measurement");
  await expect(page.getByTestId("provenance-chain")).toContainText("P1");
  await expect(page.getByTestId("provenance-chain")).toContainText("P2");
  await expect(page.getByTestId("provenance-chain")).toContainText("P3");
  await expect(page.getByTestId("provenance-chain")).toContainText("P0");
  await expect(page.getByTestId("lot-status-history")).toContainText("accepted");
});
