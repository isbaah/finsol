import { expect, test } from "@playwright/test";

test("homepage loads and shows the app name", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/Loan Management/i);
});
