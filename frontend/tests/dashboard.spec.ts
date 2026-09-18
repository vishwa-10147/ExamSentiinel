import { test, expect } from '@playwright/test';

test.describe('ExamSentinel UI Integration Tests', () => {
  const baseURL = 'http://localhost:3000';

  test('Verify Login Page UI renders', async ({ page }) => {
    await page.goto(`${baseURL}/auth/login`);
    // Look for the "Sign in" or "Log In" text dynamically
    await expect(page.locator('text=Sign In').first()).toBeVisible();
    await expect(page.locator('text=Admin:')).toBeVisible(); // The quick demo credentials block
  });

  test('Verify Registration Page UI renders', async ({ page }) => {
    await page.goto(`${baseURL}/auth/register`);
    // Just verify the page doesn't crash (404/500)
    await expect(page.locator('form')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('Dashboard correctly blocks unauthenticated users', async ({ page }) => {
    // If we try to go to the admin dashboard without logging in, it should boot us
    await page.goto(`${baseURL}/admin/dashboard`);
    
    // AuthContext should automatically redirect us to /auth/login
    await page.waitForURL(/.*\/auth\/login/);
    expect(page.url()).toContain('/auth/login');
  });
});
