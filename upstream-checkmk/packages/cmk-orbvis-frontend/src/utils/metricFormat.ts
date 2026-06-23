import { userSpecificUnit } from '@cmk/lib/unit-format/unitFormatter'

import type { MetricUnitSpec } from '@/types/api'
import { fmtSI } from '@/utils/perf'

// Seconds per raw perfdata time unit. Time scales by 60, not 1000, so an SI
// prefix on the raw unit would produce nonsense ("4.5 kms" for 4500 ms) —
// these units get a synthetic CMK time spec instead of the SI heuristic.
const TIME_UNIT_SECONDS: Record<string, number> = { ns: 1e-9, us: 1e-6, µs: 1e-6, ms: 1e-3, s: 1 }

function timeFallbackSpec(rawUnit: string): MetricUnitSpec | null {
  const scale = TIME_UNIT_SECONDS[rawUnit]
  if (scale === undefined) return null
  return { notation: 'time', symbol: 's', precision: { type: 'auto', digits: 2 }, scale }
}

/**
 * Render a raw perfdata value exactly like the Checkmk GUI: through the
 * vendored cmk-frontend-vue unit-format library, fed with the metric's
 * registered display unit (notation + symbol + precision from the CMK metric
 * registry) and the check plugin's translation scale. Without a registry
 * entry (standalone connections, unregistered metrics) it falls back to the
 * client-side SI heuristic on the raw perfdata unit — except for time units,
 * which still go through the CMK TimeFormatter via a synthetic spec.
 */
export function renderMetricValue(
  value: number,
  spec: MetricUnitSpec | null | undefined,
  rawUnit: string
): string {
  const effective = spec ?? timeFallbackSpec(rawUnit)
  if (!effective) return fmtSI(value, rawUnit)
  try {
    const { formatter, convert } = userSpecificUnit(
      { notation: effective.notation, symbol: effective.symbol, precision: effective.precision },
      'celsius'
    )
    return formatter.render(convert(value * effective.scale))
  } catch {
    // Version skew: a newer backend may emit a notation this bundle doesn't
    // know yet (makeFormatter throws) — degrade to the heuristic instead of
    // killing the component render.
    return fmtSI(value, rawUnit)
  }
}
