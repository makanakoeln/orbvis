/**
 * Copies a curated subset of Tabler Icons (MIT) to backend/builtin_icons/.
 * Run after `npm install`: npm run copy-builtin-icons
 *
 * Tabler Icons: https://tabler.io/icons — MIT License
 * Safe for open-source and commercial use.
 */

import { existsSync, mkdirSync, copyFileSync, readdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

const TABLER_DIR = join(__dirname, '..', 'node_modules', '@tabler', 'icons')
const OUT_DIR = join(__dirname, '..', '..', 'backend', 'app', 'builtin_icons')

// v3+: icons/outline/<name>.svg  |  v2: icons/<name>.svg
const ICONS_DIR_V3 = join(TABLER_DIR, 'icons', 'outline')
const ICONS_DIR_V2 = join(TABLER_DIR, 'icons')
const SRC_DIR = existsSync(ICONS_DIR_V3) ? ICONS_DIR_V3 : ICONS_DIR_V2

if (!existsSync(SRC_DIR)) {
  console.error('ERROR: @tabler/icons not found. Run `npm install` first.')
  process.exit(1)
}

// Curated set for monitoring/network visualisation.
// Names match Tabler icon filenames (without .svg).
const CURATED = [
  // Servers & compute
  'server', 'server-2', 'server-cog', 'server-bolt', 'server-off',
  'device-desktop', 'device-laptop', 'device-mobile', 'device-tablet',
  'cpu', 'cpu-2', 'disc', 'disc-off',

  // Network
  'network', 'router', 'router-2',
  'wifi', 'wifi-off',
  'antenna', 'satellite',
  'plug', 'plug-connected', 'plug-off',

  // Infrastructure
  'database', 'database-cog', 'database-off',
  'cloud', 'cloud-off', 'cloud-computing',
  'container',
  'building', 'building-2',
  'box',

  // Monitoring & metrics
  'activity', 'heart-rate-monitor',
  'chart-line', 'chart-bar',
  'gauge', 'speedometer',
  'temperature',

  // Security
  'shield', 'shield-check', 'shield-off',
  'lock', 'lock-open',
  'key',
  'firewall',

  // Topology
  'sitemap', 'hierarchy', 'hierarchy-2',
  'topology-star', 'topology-ring', 'topology-bus',
  'git-fork',

  // Status & alerts
  'alert-triangle', 'alert-circle',
  'circle-check', 'circle-x',
  'info-circle',
  'bell', 'bell-off',

  // Peripherals
  'printer', 'camera', 'camera-off',
  'phone', 'phone-off',

  // Maps & location
  'map', 'map-2', 'map-pin',
  'globe',

  // General
  'settings', 'settings-2',
  'terminal', 'code',
  'power', 'refresh',
]

mkdirSync(OUT_DIR, { recursive: true })

let copied = 0
let missing = []

for (const name of CURATED) {
  const src = join(SRC_DIR, `${name}.svg`)
  if (!existsSync(src)) {
    missing.push(name)
    continue
  }
  copyFileSync(src, join(OUT_DIR, `${name}.svg`))
  copied++
}

console.log(`Copied ${copied} icons to backend/builtin_icons/`)
if (missing.length) {
  console.warn(`Skipped (not in this Tabler version): ${missing.join(', ')}`)
}
