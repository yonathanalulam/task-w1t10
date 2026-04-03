import fs from "node:fs";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const certFile = "/certs/server.crt";
const keyFile = "/certs/server.key";
const hasTlsCerts = fs.existsSync(certFile) && fs.existsSync(keyFile);

export default defineConfig({
  plugins: [vue()],
  server: {
    host: process.env.VITE_DEV_HOST ?? "0.0.0.0",
    port: Number(process.env.VITE_DEV_PORT ?? 5173),
    https: hasTlsCerts
      ? {
          cert: fs.readFileSync(certFile),
          key: fs.readFileSync(keyFile)
        }
      : undefined,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_PROXY_TARGET ?? "https://backend:8443",
        secure: false,
        changeOrigin: true
      }
    }
  }
});
