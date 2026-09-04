/// <reference types="vitest" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    // Nur Unit-Tests. Die Playwright-Specs unter e2e/ laufen mit ihrem eigenen Runner.
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
