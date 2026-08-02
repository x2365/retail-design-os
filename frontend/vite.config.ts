import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server proxies /api to the local backend so the app can always call
// same-origin `/api/...` — in prod, nginx does the same proxying (see
// nginx.conf), so the frontend code never needs to know the API's origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5500,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
