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
            // FIRST: Workbox uses the first rule that matches, and /api/plan/competencies/ also matches the broader /api/plan/ rule below.
            // The list of skills is public reference data (no child, no teacher): shown at once from the copy kept, refreshed in the background, and NOT removed at sign-out.
            urlPattern: /^https?:\/\/.*\/api\/plan\/competencies\/.*$/,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'competency-cache', expiration: { maxEntries: 5, maxAgeSeconds: 604800 } },
          },
          {
            urlPattern: /^https?:\/\/.*\/api\/plan\/.*$/,
            handler: 'NetworkFirst',
            // networkTimeoutSeconds: on a slow or hanging connection, answer from the cached copy after 6 seconds instead of waiting for ever
            options: { cacheName: 'plan-cache', networkTimeoutSeconds: 6, expiration: { maxEntries: 30, maxAgeSeconds: 86400 } },
          },
          {
            // a teacher's worksheets (printed pages): kept for a day so they can be opened and printed with no network. Removed at sign-in and sign-out (src/services/offlineCache.js).
            urlPattern: /^https?:\/\/.*\/api\/worksheet\/.*$/,
            handler: 'NetworkFirst',
            options: { cacheName: 'worksheet-cache', networkTimeoutSeconds: 6, expiration: { maxEntries: 30, maxAgeSeconds: 86400 } },
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
