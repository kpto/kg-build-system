import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

/**
 * The model tests import domain ViewModels directly, and those modules use the
 * `@/` source alias. The browser never sees this config; it exists so the
 * conceptual hierarchy can be built and asserted without React or the DOM.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
