/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import vue from '@vitejs/plugin-vue'
import { existsSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { URL, fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

const pkg = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf-8')
) as { version: string }

const CMK_SRC = fileURLToPath(new URL('../cmk-frontend-vue/src', import.meta.url))
const OWN_SRC = fileURLToPath(new URL('./src', import.meta.url))

// The OrbVis SPA ships as static files under
// share/check_mk/web/htdocs/cmk-orbvis-frontend/ and is served behind
// the per-site Apache at /<site>/orbvis/. A relative base keeps every
// asset reference working no matter which URL prefix serves the bundle.
export default defineConfig({
  plugins: [
    vue(),
    {
      // cmk-frontend-vue sources import their own modules as '@/...'.
      // Vite's alias rewrites '@' to OUR src before plugins run, so
      // imports originating from a cmk-frontend-vue file must be
      // redirected back into the cmk tree. OrbVis files shadow cmk
      // paths only when the cmk candidate does not exist — the two
      // source trees do not overlap.
      name: 'cmk-self-alias-resolver',
      enforce: 'pre' as const,
      resolveId(source: string, importer: string | undefined) {
        if (!importer || !importer.startsWith(CMK_SRC + path.sep)) return
        if (!source.startsWith(OWN_SRC + path.sep)) return
        const base = path.resolve(CMK_SRC, source.slice(OWN_SRC.length + 1))
        for (const ext of ['', '.ts', '.vue', '/index.ts', '/index.vue']) {
          const cand = base + ext
          if (existsSync(cand) && statSync(cand).isFile()) return cand
        }
        return
      }
    }
  ],
  base: '',
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version)
  },
  resolve: {
    alias: [
      { find: '@cmk', replacement: fileURLToPath(new URL('../cmk-frontend-vue/src', import.meta.url)) },
      { find: '@', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
      // cmk-frontend-vue resolves theme icons through this alias
      // (see its vite.config.ts) — required by CmkIcon's constants.
      { find: '~cmk-frontend', replacement: fileURLToPath(new URL('../cmk-frontend/dist', import.meta.url)) }
    ]
  },
  server: {
    port: 5174,
    proxy: {
      // Dev mode proxies API calls to a site-local OrbVis backend.
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        ws: true
      },
      '/boards/backgrounds': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/images': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  },
  build: {
    // No explicit browser target list: inherit Vite's default baseline,
    // matching cmk-frontend-vue (the external repo's legacy target list
    // predates Vite 7's minimum).
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      onLog(level, log, handler) {
        // vue3-gettext pulls in pofile for its node-side tooling; the
        // runtime never reaches that branch (same waiver as in
        // cmk-frontend-vue's onwarn handler).
        if (log.plugin === 'vite:resolve' && log.message.includes('pofile')) return
        handler(level, log)
      },
      output: {
        manualChunks(id: string) {
          if (/node_modules\/d3[/-]/.test(id)) return 'd3'
          if (/node_modules\/(echarts|vue-echarts)\//.test(id)) return 'echarts'
        }
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}']
  }
})
