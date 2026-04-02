// Multiplier for single-char SI prefix units (e.g. "k" = kilobytes in Checkmk perf_data)
export const _SI_MULT: Record<string, number> = {
  k: 1e3,
  K: 1e3,
  m: 1e6,
  M: 1e6,
  g: 1e9,
  G: 1e9,
  t: 1e12,
  T: 1e12,
};

export const CHART_PALETTE = [
  '#6366f1',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#f97316',
  '#ec4899',
];

// Max series shown in the legend and used for Y-domain calculation
export const MAX_VISIBLE_SERIES = 6;

// True when the unit is a bare SI magnitude prefix that fmtMetricVal absorbs into its output
export function isSingleCharSIPrefix(unit: string | null | undefined): boolean {
  return !!unit && unit.length === 1 && _SI_MULT[unit] !== undefined;
}

// Returns the base unit after stripping any SI prefix that fmtMetricVal absorbs.
// Examples: "MB" → "B", "k" → "", "%" → "%", "" → ""
export function baseUnit(unit: string | null | undefined): string {
  if (!unit) return '';
  if (isSingleCharSIPrefix(unit)) return '';
  if (/^[kKmMgGtT]/.test(unit) && unit.length > 1) return unit.slice(1);
  return unit;
}

export function fmtMagnitude(v: number): string {
  if (v === 0) return '0';
  const a = Math.abs(v);
  if (a >= 1e12) return `${(v / 1e12).toFixed(1)}T`;
  if (a >= 1e9) return `${(v / 1e9).toFixed(1)}G`;
  if (a >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
  return a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
}

export function fmtMetricVal(v: number, unit?: string): string {
  // Single-char SI prefix units (e.g. "k" = kilobytes): scale to base unit so the
  // magnitude formatting produces the correct combined prefix (116200 k → "116.2M").
  if (isSingleCharSIPrefix(unit)) return fmtMagnitude(v * _SI_MULT[unit!]);
  if (!unit || !/^[kKmMgGtT]/.test(unit)) return fmtMagnitude(v);
  // Multi-char prefixed unit (e.g. "MB", "kB"): scale by SI prefix factor so magnitude
  // formatting produces a readable combined value ("116130 MB" → "116.1G" + base "B").
  return fmtMagnitude(v * (_SI_MULT[unit[0]] ?? 1));
}

// Converts a raw perf_data value to its base unit for use as ECharts series data.
// ECharts handles scaling internally, so all series values must be in a consistent base unit.
export function normalizeMetricValue(v: number, unit?: string): number {
  if (isSingleCharSIPrefix(unit)) return v * _SI_MULT[unit!];
  if (!unit || !/^[kKmMgGtT]/.test(unit)) return v;
  return v * (_SI_MULT[unit[0]] ?? 1);
}
