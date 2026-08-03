import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3015,
    proxy: {
      "/api": "http://127.0.0.1:5000",
      "/health": "http://127.0.0.1:5000",
      "/ready": "http://127.0.0.1:5000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
