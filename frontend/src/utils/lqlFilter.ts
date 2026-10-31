// Client-side mirror of backend ``normalize_object_filter``: one or more
// Filter:/And:/Or:/Negate: lines, separated by real or NagVis-style literal
// ``\n``. Lets the settings modal flag a bad filter before saving and keeps
// half-typed filters out of the live preview.
const SAFE_FILTER_LINE = /^(?:Filter|And|Or|Negate): .+$/

export function isValidLqlFilter(value: string): boolean {
  const lines = value
    .replaceAll('\\n', '\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  return lines.length > 0 && lines.every((line) => SAFE_FILTER_LINE.test(line))
}
