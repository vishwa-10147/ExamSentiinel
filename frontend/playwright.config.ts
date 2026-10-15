import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3110',
    trace: 'on-first-retry',
    headless: true,
    // For a staging stack with a self-signed certificate (deploy/rehearsal).
    ignoreHTTPSErrors: !!process.env.PLAYWRIGHT_IGNORE_HTTPS_ERRORS,
  },
  // Start a dev server only when not pointed at a running app. Two `next dev`
  // processes must never share one .next directory: they corrupt each other's chunks.
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: 'npm run dev -- -p 3110',
        url: 'http://127.0.0.1:3110',
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
      },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
