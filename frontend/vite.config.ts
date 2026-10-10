import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Auf allen Netzwerk-Interfaces lauschen (0.0.0.0), damit die UI auch von
    // anderen Geraeten im LAN erreichbar ist (z. B. http://192.168.0.52:5173).
    // Standardmaessig bindet Vite nur an localhost.
    host: true,
    // Backend-API im Dev-Modus durchreichen (FastAPI auf Port 8000).
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
