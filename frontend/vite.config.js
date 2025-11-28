import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'

// Check if certificates exist (for HTTPS support)
const certsPath = '/app/certs'
const keyPath = path.join(certsPath, 'server.key')
const certPath = path.join(certsPath, 'server.crt')

// Determine if we can use HTTPS
const useHttps = fs.existsSync(keyPath) && fs.existsSync(certPath)

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: useHttps ? {
      key: fs.readFileSync(keyPath),
      cert: fs.readFileSync(certPath),
    } : false,
    proxy: {
      '/api': {
        target: 'https://backend:8000',
        changeOrigin: true,
        secure: false, // Accept self-signed certificates
      }
    }
  }
})

