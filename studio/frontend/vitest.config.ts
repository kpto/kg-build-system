import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Vitest runs the store and renderer logic that the shell is built on — the IR
 * renderers, the optimistic write/409 reconciliation, the coalescing window, the undo
 * stack, the problem indices — plus the component that carries the most behaviour,
 * `TypePicker`. jsdom is the default environment because the component test needs a
 * DOM and the store tests do not care.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
