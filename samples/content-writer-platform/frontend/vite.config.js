import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/writer-writer-endpoint': {
        target: 'http://default-default.am-gateway.localhost:19080',
        changeOrigin: true,
      }
    }
  }
})
