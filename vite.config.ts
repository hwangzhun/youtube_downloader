import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "frontend",
  plugins: [react()],
  clearScreen: false,
  server: {
    host: "127.0.0.1",
    port: 5188,
    strictPort: true,
  },
  envPrefix: ["VITE_", "TAURI_ENV_"],
  build: {
    target: "chrome105",
    outDir: "../dist-web",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./frontend/src/test/setup.ts"],
  },
});
