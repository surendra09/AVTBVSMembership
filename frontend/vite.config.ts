/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5173,
    // Same-origin API in development so HttpOnly cookies work exactly as in production.
    proxy: { "/api": { target: process.env.VITE_API_PROXY ?? "http://127.0.0.1:8000", changeOrigin: false } },
  },
  build: {
    sourcemap: false,
    outDir: "dist",
    rollupOptions: { output: { manualChunks: { vendor: ["react", "react-dom", "react-router-dom"], forms: ["react-hook-form", "zod", "@hookform/resolvers"] } } },
  },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"], globals: true, css: false },
});
