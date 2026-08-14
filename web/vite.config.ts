import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  build: {
    // nginx sirve estos archivos directamente; no hay Node en producción.
    outDir: "dist",
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      // En desarrollo, la API la sirve uvicorn en 8000. En producción es el mismo origen.
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
