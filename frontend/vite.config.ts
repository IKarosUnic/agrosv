import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo el API corre en 8000 (uvicorn) y Vite reenvía /api.
// En producción FastAPI sirve `dist/` desde el mismo origen.
export default defineConfig({
  plugins: [react()],
  build: { sourcemap: false, chunkSizeWarningLimit: 900 },
  server: {
    port: 5173,
    host: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
