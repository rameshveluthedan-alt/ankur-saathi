import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['ankur-saathi-icon.svg'],
      manifest: {
        name: 'Ankur Saathi — अंकुर साथी',
        short_name: 'अंकुर साथी',
        description: 'AI-powered daily differentiated instruction for FLN classrooms',
        theme_color: '#2D6A4F',
        background_color: '#FAFAF8',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          { src: '/ankur-saathi-icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/ankur-saathi-icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /^https?:\/\/.*\/api\/plan\/.*$/,
            handler: 'NetworkFirst',
            options: { cacheName: 'plan-cache', expiration: { maxEntries: 30, maxAgeSeconds: 86400 } },
          },
          {
            urlPattern: /^https?:\/\/.*\/api\/plan\/competencies\/.*$/,
            handler: 'CacheFirst',
            options: { cacheName: 'competency-cache', expiration: { maxEntries: 5, maxAgeSeconds: 604800 } },
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
