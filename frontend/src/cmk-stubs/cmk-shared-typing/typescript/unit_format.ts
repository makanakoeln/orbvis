// Hand-written stub mirroring cmk-shared-typing/source/unit_format.json —
// the canonical wire format the Checkmk backend serializes unit specs into.
// OrbVis' /metrics/units endpoint emits the same shape.

export interface Precision {
  type: 'auto' | 'strict'
  digits: number
}

export interface UnitFormat {
  notation: 'decimal' | 'si' | 'iec' | 'standard_scientific' | 'engineering_scientific' | 'time'
  symbol: string
  precision: Precision
  /**
   * Whether this unit is eligible for auto-conversion (currently only
   * Celsius <-> Fahrenheit). Defaults to true. Custom-graph user-defined
   * units set this to false so a literal "°C" label is not treated as a
   * temperature.
   */
  convertible?: boolean
}
