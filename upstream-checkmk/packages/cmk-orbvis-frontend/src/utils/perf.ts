export interface PerfMetric {
  label: string
  value: number
  unit: string
  warn: number | null
  crit: number | null
  min: number | null
  max: number | null
}

/** Parse Nagios/Checkmk performance data string into structured metrics. */
export function parsePerfData(raw: string): PerfMetric[] {
  if (!raw) return []
  const metrics: PerfMetric[] = []
  // Split on whitespace, but labels can be quoted: 'label with space'=value
  const parts = raw.match(/(?:'[^']+'|[^\s]+)=[^\s]*/g) ?? []
  for (const part of parts) {
    const eq = part.indexOf('=')
    if (eq < 0) continue
    const label = part.slice(0, eq).replace(/^'|'$/g, '')
    const rest = part.slice(eq + 1)
    const [valStr = '', warnStr, critStr, minStr, maxStr] = rest.split(';')
    // Allow "/" inside the unit so multi-char units like "B/s" don't get
    // truncated to just "B" (which would lose the per-second qualifier).
    const valMatch = valStr.match(/^(-?[\d.]+)([a-zA-Z%/]*)/)
    if (!valMatch) continue
    const [, num, unit] = valMatch
    if (num === undefined) continue
    const toNum = (s?: string) => (s !== undefined && s !== '' ? parseFloat(s) : null)
    metrics.push({
      label,
      value: parseFloat(num),
      unit: unit || '',
      warn: toNum(warnStr),
      crit: toNum(critStr),
      min: toNum(minStr),
      max: toNum(maxStr)
    })
  }
  return metrics
}

/** Get the first matching metric by label, or the first metric if label is empty. */
export function getMetric(metrics: PerfMetric[], label?: string | null): PerfMetric | null {
  const first = metrics[0]
  if (first === undefined) return null
  if (!label) return first
  return metrics.find((m) => m.label === label) ?? first
}

/** Calculate utilization percentage (0–100) for a metric. */
export function utilPercent(m: PerfMetric): number {
  if (m.max !== null && m.max > 0) return Math.min(100, Math.max(0, (m.value / m.max) * 100))
  if (m.crit !== null && m.crit > 0) return Math.min(100, Math.max(0, (m.value / m.crit) * 100))
  if (m.unit === '%') return Math.min(100, Math.max(0, m.value))
  return 0
}

/** Map utilization percentage to a color: green → amber → red. */
export function utilColor(pct: number): string {
  if (pct <= 50) {
    const t = pct / 50
    const r = Math.round(34 + (245 - 34) * t)
    const g = Math.round(197 + (158 - 197) * t)
    const b = Math.round(94 + (11 - 94) * t)
    return `rgb(${r},${g},${b})`
  } else {
    const t = (pct - 50) / 50
    const r = Math.round(245 + (239 - 245) * t)
    const g = Math.round(158 + (68 - 158) * t)
    const b = Math.round(11 + (68 - 11) * t)
    return `rgb(${r},${g},${b})`
  }
}
