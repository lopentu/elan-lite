import { test, expect } from "@playwright/test";
test("edit persists, lexicon rename links, query, review and synchronized overlay", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("#project-name")).toContainText("Synthetic");
  await page.locator(".interval").first().click();
  await page.locator("#value").fill("UI edited annotation");
  await page.locator("#annotation-form button[type=submit]").click();
  await expect(page.locator("#notice")).toContainText("saved to SQLite");
  await page.reload();
  await page.locator(".interval").first().click();
  await expect(page.locator("#value")).toHaveValue("UI edited annotation");
  await page.locator(".lex-item").first().click();
  await page.locator("#gloss").fill("RENAMED-DEMO");
  await page.locator("#lexicon-form button[type=submit]").click();
  await expect(page.locator(".interval").first()).toContainText("RENAMED-DEMO");
  await page.locator("#query-form button").click();
  await expect(page.locator(".query-item")).toHaveCount(2);
  await page.locator("#propose").click();
  await expect(page.locator(".suggestion").first()).toContainText("pending");
  await page
    .locator(".suggestion")
    .first()
    .getByRole("button", { name: "接受 / Accept" })
    .click();
  await expect(page.locator(".suggestion").first()).toContainText("accepted");
  await page
    .locator(".suggestion")
    .first()
    .getByRole("button", { name: "復原 / Undo" })
    .click();
  await expect(page.locator(".suggestion").first()).toContainText("pending");
  await page
    .locator(".suggestion")
    .first()
    .getByRole("button", { name: "拒絕 / Reject" })
    .click();
  await expect(page.locator(".suggestion").first()).toContainText("rejected");
  await page.locator("#seek").fill("2000");
  await page.locator("#seek").dispatchEvent("input");
  await expect(page.locator("#pose")).toHaveAttribute("data-frame", "2000");
  await expect(page.locator("#clock")).toHaveText("00:02.000");
  await expect(page.locator("#pose circle")).toHaveCount(8);
  await page.getByText("空間位置 / Spatial loci", { exact: true }).click();
  await page.locator("#locus").click();
  await expect(page.locator("#notice")).toContainText("Locus saved");
  await expect(page.locator("#pose circle")).toHaveCount(9);
  await page.locator("#seek").fill("1000");
  await page.locator("#seek").dispatchEvent("input");
  await expect(page.locator("#pose")).toHaveAttribute("data-frame", "1000");
  await expect(page.locator("#pose circle")).toHaveCount(8);
  await page.screenshot({ path: "/tmp/elan-lite-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "/tmp/elan-lite-mobile.png", fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});
test("unsupported EAF import shows explicit blocker", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#project-name")).toContainText("Synthetic");
  await page
    .locator("#eaf-input")
    .setInputFiles({
      name: "unsupported.eaf",
      mimeType: "application/xml",
      buffer: Buffer.from(
        '<ANNOTATION_DOCUMENT VERSION="3.0"><HEADER/><TIME_ORDER/><REF_ANNOTATION ANNOTATION_REF="cycle"/></ANNOTATION_DOCUMENT>',
      ),
    });
  await expect(page.locator("#notice")).toContainText("Import blocked");
});
