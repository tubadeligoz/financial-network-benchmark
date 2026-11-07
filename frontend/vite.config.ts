import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/docs': 'http://127.0.0.1:8000', '/openapi.json': 'http://127.0.0.1:8000' } },
  test: { environment: 'jsdom', setupFiles: ['./tests/setup.ts'], include: ['tests/**/*.test.ts', 'tests/**/*.test.tsx'] },
  build: { chunkSizeWarningLimit: 800, rollupOptions: { output: { manualChunks: { charts: ['echarts/core','echarts/charts','echarts/components','echarts/renderers'], network: ['cytoscape'] } } } },
});
