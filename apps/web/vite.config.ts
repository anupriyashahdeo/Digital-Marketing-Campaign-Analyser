import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local: API on localhost:8000. Docker sets API_URL=http://api:8000.

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": process.env.API_URL ?? "http://localhost:8000" } },
});
