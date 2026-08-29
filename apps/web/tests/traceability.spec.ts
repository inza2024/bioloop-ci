import { expect, test, type Page } from "@playwright/test";

const openTraceabilityWorkflow = async (page: Page) => {
  await page.goto("/");
  await page.getByTestId("quantity-input").fill("1500");
  await page.getByRole("button", { name: "Enregistrer et chercher une unité" }).click();
  await page.getByTestId("generate-proposal").click();
  await expect(page.getByTestId("traceability-workflow")).toBeVisible();
};

const traceabilityOverflow = async (page: Page) =>
  page.locator(".trace-card").evaluateAll((cards) => {
    const tolerance = 0.5;

    return cards.flatMap((card, index) => {
      const title = card.querySelector<HTMLElement>(".trace-card-title");
      const badge = card.querySelector<HTMLElement>(".trace-card-title .evidence");
      const heading = title?.querySelector<HTMLElement>("h3");
      if (!title || !badge || !heading) return [`carte ${index + 1}: en-tête ou badge absent`];

      const cardBox = card.getBoundingClientRect();
      const titleBox = title.getBoundingClientRect();
      const badgeBox = badge.getBoundingClientRect();
      const defects: string[] = [];

      if (titleBox.left < cardBox.left - tolerance || titleBox.right > cardBox.right + tolerance) {
        defects.push(`carte ${index + 1}: en-tête hors carte`);
      }
      if (badgeBox.left < cardBox.left - tolerance || badgeBox.right > cardBox.right + tolerance) {
        defects.push(`carte ${index + 1}: badge hors carte`);
      }
      if (badge.scrollWidth > badge.clientWidth + 2) {
        defects.push(`carte ${index + 1}: contenu du badge tronqué`);
      }
      if (heading.scrollWidth > heading.clientWidth + 2) {
        defects.push(`carte ${index + 1}: titre non réductible`);
      }
      return defects;
    });
  });

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

test("les badges de traçabilité restent dans leurs cartes aux largeurs responsive et à l’impression", async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 1000 });
  await openTraceabilityWorkflow(page);

  const viewports = [
    { label: "desktop", width: 1440, height: 1000 },
    { label: "intermédiaire", width: 820, height: 1000 },
    { label: "tablette", width: 768, height: 1024 },
    { label: "mobile", width: 390, height: 844 },
  ];

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    expect.soft(await traceabilityOverflow(page), viewport.label).toEqual([]);

    const workflowWidth = await page.locator(".trace-steps").evaluate((element) => ({
      client: element.clientWidth,
      scroll: element.scrollWidth,
    }));
    expect.soft(workflowWidth.scroll, `${viewport.label}: débordement horizontal des cartes`).toBeLessThanOrEqual(workflowWidth.client);
  }

  await page.setViewportSize({ width: 1200, height: 1123 });
  await page.emulateMedia({ media: "print" });
  expect(await traceabilityOverflow(page), "impression A4").toEqual([]);
  const printWidth = await page.locator(".trace-steps").evaluate((element) => ({
    client: element.clientWidth,
    scroll: element.scrollWidth,
  }));
  expect(printWidth.scroll, "impression A4: débordement horizontal des cartes").toBeLessThanOrEqual(printWidth.client);
  const printColumns = await page.locator(".trace-steps").evaluate(
    (element) => getComputedStyle(element).gridTemplateColumns.split(" ").length,
  );
  expect(printColumns, "impression A4: nombre de colonnes").toBe(1);
});
