import { test, expect } from "@playwright/test";

test("la página / renderiza 'DOCYAN — boot OK'", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("boot-status")).toHaveText("DOCYAN — boot OK");
});
