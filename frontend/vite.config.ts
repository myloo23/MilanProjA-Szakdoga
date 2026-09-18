import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Fejlesztés közben (`npm run dev`) a fürtben futó nginx helyett a Vite
// dev szerver továbbítja az /api/ kéréseket a helyben futó backendnek,
// ugyanúgy levágva az előtagot. Így a kód mindkét környezetben /api/-t hív.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
