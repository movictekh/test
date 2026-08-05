import { fileURLToPath, URL } from 'node:url'

import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
      disableLogging: true,
    }),
    react(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    clearMocks: true,
    restoreMocks: true,
    mockReset: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      reportsDirectory: './coverage',
      exclude: [
        'src/main.tsx',
        'src/routeTree.gen.ts',
        'src/mocks/**',
        '**/*.stories.tsx',
        '**/*.d.ts',
      ],
    },
  },
})
