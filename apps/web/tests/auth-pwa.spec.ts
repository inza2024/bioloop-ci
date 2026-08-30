import { expect, test, type Page } from "@playwright/test";


async function registerProducer(page: Page, suffix: string) {
  await page.goto("/#pilot-access");
  await page.getByRole("button", { name: "Créer un compte", exact: true }).click();
  await page.getByTestId("register-name").fill("Awa Pilote E2E");
  await page.getByTestId("register-organization").fill("Ferme pilote E2E");
  await page.getByTestId("register-organization-type").selectOption("producer");
  await page.getByTestId("auth-email").fill(`awa-${suffix}@example.test`);
  await page.getByTestId("auth-password").fill("BioLoopPilot2026");
  await page.getByTestId("pilot-auth-submit").click();
  await expect(page).toHaveURL(/\/portal\/producer$/);
  await expect(page.getByTestId("authenticated-portal")).toContainText("Awa Pilote E2E");
}

test("inscription pilote, redirection par rôle et déconnexion sans auth localStorage", async ({ page }) => {
  await registerProducer(page, `${Date.now()}-auth`);
  await expect(page.getByText("Appartenance active")).toBeVisible();
  await expect(page.getByText(/non certifiée pour la production/).first()).toBeVisible();

  await page.goto("/portal/client_farmer");
  await expect(page).toHaveURL(/\/portal\/producer$/);

  const authStorage = await page.evaluate(() => ({
    local: Object.keys(localStorage).filter((key) => /auth|token|session/i.test(key)),
    session: Object.keys(sessionStorage).filter((key) => /auth|token|session/i.test(key)),
  }));
  expect(authStorage).toEqual({ local: [], session: [] });

  await page.getByRole("button", { name: "Se déconnecter" }).click();
  await expect(page).toHaveURL(/\/#pilot-access$/);
});

test("manifest PWA, shell public et responsive 390/768/1024/desktop", async ({ page, request }) => {
  const manifestResponse = await request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBeTruthy();
  const manifest = await manifestResponse.json();
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons).toHaveLength(2);

  const worker = await request.get("/sw.js");
  expect(worker.ok()).toBeTruthy();
  const workerSource = await worker.text();
  expect(workerSource).toContain('url.pathname.startsWith("/api/")');
  expect(workerSource).toContain('url.pathname.startsWith("/portal/")');

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 768, height: 1024 },
    { width: 1024, height: 900 },
    { width: 1440, height: 1000 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByTestId("pwa-status")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    const offenders = overflow > 1 ? await page.locator("body *").evaluateAll((elements) =>
      elements.flatMap((element) => {
        const box = element.getBoundingClientRect();
        return box.right > document.documentElement.clientWidth + 1 || box.left < -1
          ? [`${element.tagName.toLowerCase()}.${element.className}: ${Math.round(box.left)}..${Math.round(box.right)}`]
          : [];
      }).slice(0, 12),
    ) : [];
    expect(overflow, `${viewport.width}px sans débordement horizontal — ${offenders.join(" | ")}`).toBeLessThanOrEqual(1);
  }
});

test("une déclaration hors ligne est mise en file puis synchronisée une seule fois", async ({ page, context }) => {
  const suffix = `${Date.now()}-offline`;
  await registerProducer(page, suffix);
  await page.goto("/");
  await expect(page.getByTestId("pilot-session")).toBeVisible();
  await expect(page.getByTestId("quantity-input")).toBeVisible();

  await context.setOffline(true);
  await expect(page.getByTestId("pwa-status")).toContainText("Hors connexion");
  await page.getByTestId("quantity-input").fill("777");
  await page.getByRole("button", { name: "Enregistrer et chercher une unité" }).click();
  await expect(page.getByTestId("offline-queued")).toContainText("mise en attente");
  await expect(page.getByTestId("offline-queued")).toContainText("Aucune preuve");

  await context.setOffline(false);
  await expect(page.getByTestId("pwa-status")).toContainText("En ligne");
  await expect(page.getByTestId("pwa-status")).not.toContainText("à synchroniser", { timeout: 15_000 });
  await page.getByRole("button", { name: "Ouvrir mon portail" }).click();
  await expect(page.getByTestId("authenticated-portal")).toContainText("777 kg");
  await expect(page.locator(".portal-object-card")).toHaveCount(1);
});
