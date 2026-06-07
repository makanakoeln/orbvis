// vue-gettext-compile emits keys in .po order, churning the tracked JSON on
// every build — rewrite sorted so the output is deterministic.
import { readFileSync, readdirSync, writeFileSync } from 'node:fs'

const dir = new URL('../src/assets/locale/', import.meta.url)

function sortDeep(value) {
  if (Array.isArray(value)) return value.map(sortDeep)
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((k) => [k, sortDeep(value[k])])
    )
  }
  return value
}

for (const name of readdirSync(dir).filter((n) => n.endsWith('.json'))) {
  const file = new URL(name, dir)
  writeFileSync(file, JSON.stringify(sortDeep(JSON.parse(readFileSync(file, 'utf-8')))) + '\n')
}
