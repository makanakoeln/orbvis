import { userSpecificUnit } from '@cmk/lib/unit-format/unitFormatter'

import type { MetricUnitSpec } from '@/types/api'
import { fmtSI } from '@/utils/perf'

/**
 * Render a raw perfdata value exactly like the Checkmk GUI: through the
 * vendored cmk-frontend-vue unit-format library, fed with the metric's
 * registered display unit (notation + symbol + precision from the CMK metric
 * registry) and the check plugin's translation scale. Without a registry
 * entry (standalone connections, unregistered metrics) it falls back to the
 * client-side SI heuristic on the raw perfdata unit.
 */
export function renderMetricValue(
  value: number,
  spec: MetricUnitSpec | null | undefined,
  rawUnit: string
): string {
  if (!spec) return fmtSI(value, rawUnit)
  try {
    const { formatter, convert } = userSpecificUnit(
      { notation: spec.notation, symbol: spec.symbol, precision: spec.precision },
      'celsius'
    )
    return formatter.render(convert(value * spec.scale))
  } catch {
    // Version skew: a newer backend may emit a notation this bundle doesn't
    // know yet (makeFormatter throws) — degrade to the heuristic instead of
    // killing the component render.
    return fmtSI(value, rawUnit)
  }
}
