import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true, // bind 0.0.0.0 — wajib untuk akses via ngrok dari luar
    allowedHosts: ['.ngrok-free.app', '.ngrok.app', '.ngrok.io'], // izinkan host ngrok (anti DNS rebinding tetap aktif untuk host lain)
    proxy: {
      // Dev: semua panggilan /api diteruskan ke backend lokal
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
