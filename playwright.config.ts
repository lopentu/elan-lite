import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/ui",
  use: {
    baseURL: "http://127.0.0.1:8766",
    headless: true,
    launchOptions: { executablePath: process.env.CHROMIUM_PATH },
  },
  webServer: {
    command:
      "python -m backend.server --port 8766 --db /tmp/elan-lite-ui-" +
      Date.now() +
      ".sqlite",
    url: "http://127.0.0.1:8766",
    reuseExistingServer: false,
  },
});
