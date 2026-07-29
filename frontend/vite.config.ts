import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/check": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/ready": "http://localhost:8000",
      "/feedback": "http://localhost:8000",
      "/metrics": "http://localhost:8000",
    },
  },
});
