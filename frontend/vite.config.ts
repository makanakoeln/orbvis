import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const appVersion = readFileSync(new URL('../VERSION', import.meta.url), 'utf-8').trim()

const CMK_VENDOR = fileURLToPath(new URL('./src/vendor/cmk', import.meta.url))
const CMK_SRC = process.env.CMK_FRONTEND_VUE_SRC
  ? path.resolve(process.env.CMK_FRONTEND_VUE_SRC)
  : CMK_VENDOR

const ORBVIS_SRC = fileURLToPath(new URL('./src', import.meta.url))

const CMK_STUBS: Record<string, string> = {
  // CmkIcon: vendored vendor builds runtime URLs (see CmkIcon/utils.ts) and
  // can be used directly. Only CmkMultitoneIcon still needs the stub because
  // its multi-tone SVG handling assumes the Vite asset graph.
  [`${CMK_SRC}/components/CmkIcon/CmkMultitoneIcon.vue`]: `${ORBVIS_SRC}/components/cmk-stubs/CmkMultitoneIcon.vue`,
}

const isCmkFile = (id: string) =>
  id.includes('cmk-frontend-vue') || id.startsWith(CMK_VENDOR + path.sep)

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'cmk-alias-resolver',
      enforce: 'pre',
      resolveId(source, importer) {
        if (!importer || !isCmkFile(importer)) return
        // Stub out CMK-internal components that have unbundleable dependencies
        if (source in CMK_STUBS) return { id: CMK_STUBS[source] }
        // Relative imports from vendor files — resolve and check for stubs
        if (source.startsWith('.')) {
          const resolved = path.resolve(path.dirname(importer), source)
          if (resolved in CMK_STUBS) return { id: CMK_STUBS[resolved] }
          for (const ext of ['.ts', '.vue', '/index.ts', '/index.vue']) {
            if (resolved + ext in CMK_STUBS) return { id: CMK_STUBS[resolved + ext] }
          }
          return
        }
        // Case 1: raw @/ import (before Vite alias runs)
        if (source.startsWith('@/')) {
          const resolved = path.resolve(CMK_SRC, source.slice(2))
          if (resolved in CMK_STUBS) return { id: CMK_STUBS[resolved] }
          // Probe extensions/index files for directory imports (e.g. `@/components/CmkIcon`).
          for (const ext of ['', '.ts', '.vue', '/index.ts', '/index.vue']) {
            if (existsSync(resolved + ext)) return { id: resolved + ext }
          }
          return { id: resolved }
        }
        // Case 2: Vite already resolved @/ to OrbVis src path — redirect to CMK src
        if (source.startsWith(ORBVIS_SRC) && !source.includes('/cmk-stubs/')) {
          const relative = source.slice(ORBVIS_SRC.length + 1)
          const base = path.resolve(CMK_SRC, relative)
          if (base in CMK_STUBS) return { id: CMK_STUBS[base] }
          for (const ext of ['.ts', '.vue', '/index.ts', '/index.vue', '']) {
            if (existsSync(base + ext)) return { id: base + ext }
          }
        }
      },
    },
  ],
  base: process.env.VITE_BASE_PATH ?? '/',
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@cmk': CMK_SRC,
      'cmk-shared-typing': fileURLToPath(new URL('./src/cmk-stubs/cmk-shared-typing', import.meta.url)),
      'pofile': fileURLToPath(new URL('./src/vendor/empty-module.ts', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (_err, _req, res) => {
            if ('writeHead' in res && !res.headersSent) {
              res.writeHead(503, { 'Content-Type': 'text/plain' })
              res.end('Backend restarting')
            }
          })
        },
      },
      '/boards/backgrounds': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: ['chrome88', 'edge88', 'firefox78', 'safari14'],
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      onLog(level, log, handler) {
        if (log.plugin === 'vite:resolve' && log.message.includes('pofile')) return
        handler(level, log)
      },
      output: {
        manualChunks(id) {
          if (/node_modules\/d3[/-]/.test(id)) return 'd3'
          if (/node_modules\/(echarts|vue-echarts)\//.test(id)) return 'echarts'
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    // Vitest discovers unit tests under src/. e2e/ uses Playwright and must
    // not be picked up as a Vitest suite (`@playwright/test` defines its own
    // `test` global which conflicts with Vitest's).
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/**/*.test.ts',
        'src/test-setup.ts',
        'src/main.ts',
        'src/vendor/**', // third-party CMK stubs
        'src/cmk-stubs/**',
      ],
      // Baseline aus current state (~7% wenn Vue-Views mitgezaehlt werden —
      // viele views/* und components/* sind komplett untested). Folge-PRs heben
      // die Schwellen inkrementell an, Ziel 30%. Schwellen mit ~1pp Puffer
      // unter den aktuellen Ist-Werten, damit kleine PRs nicht zufällig brechen.
      thresholds: {
        lines: 6,
        functions: 4,
        branches: 3,
        statements: 6,
      },
    },
  },
})
