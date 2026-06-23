import type { TranslateFn } from '@/i18n'
import { useObjectOptionsStore } from '@/stores/objectOptions'
import type { ObjectType } from '@/types/api'

// Maps backend ``name`` → translated title. The backend ships english
// titles too (used for FormSpec dropdowns where translations don't run),
// but the per-object EditPanel reads through this map so existing
// translations keep working. Unknown names fall back to the backend
// title — that means a new style added in the registry shows up
// immediately, just untranslated until someone adds an entry here.
function lineStyleTitles(_t: TranslateFn): Record<string, string> {
  return {
    plain: _t('Simple line'),
    dashed: _t('Dashed'),
    arrow_end: _t('Arrow →'),
    arrow_start: _t('Arrow ←'),
    arrow_both: _t('Double arrow ↔'),
    arrow_inward: _t('Double arrow (middle) →←')
  }
}

// Hard-coded list the very first paint uses — once the store has
// loaded (typically a few hundred ms after login) the registry takes
// over and any new styles surface here automatically.
const LINE_STYLE_FALLBACK: { name: string; title: string }[] = [
  { name: 'plain', title: 'Simple line' },
  { name: 'dashed', title: 'Dashed' },
  { name: 'arrow_end', title: 'Arrow at end' },
  { name: 'arrow_start', title: 'Arrow at start' },
  { name: 'arrow_both', title: 'Arrows on both ends' },
  { name: 'arrow_inward', title: 'Arrows pointing inward' }
]

// The graph object type is still experimental and opt-out via the System
// Settings feature flag (``includeGraph``, on by default). When off it's hidden
// from the add-object picker; existing graph objects keep rendering.
export function placeableObjectTypes(
  _t: TranslateFn,
  includeGraph = true
): { name: ObjectType; title: string }[] {
  const types: { name: ObjectType; title: string }[] = [
    { name: 'host', title: _t('Host') },
    { name: 'service', title: _t('Service') },
    { name: 'hostgroup', title: _t('Hostgroup') },
    { name: 'servicegroup', title: _t('Servicegroup') },
    { name: 'dyngroup', title: 'Dynamic group' },
    { name: 'map', title: _t('Map link') },
    { name: 'aggregation', title: _t('BI aggregation') },
    { name: 'line', title: _t('Line') },
    { name: 'textbox', title: _t('Textbox') },
    { name: 'image', title: _t('Image') }
  ]
  if (includeGraph) {
    types.push({ name: 'graph', title: `${_t('Graph')} (experimental)` })
  }
  return types
}

// The folder-tree map type is opt-in via the System Settings feature flag.
// ``includeFolderTree`` is the resolved flag; when off the type is hidden from
// the picker (existing folder maps still render). It stays listed when the
// map being edited is already a folder map, so its type isn't silently lost.
export function mapTypeOptions(
  _t: TranslateFn,
  includeFolderTree = false,
  includePresentation = false
) {
  const options = [
    { name: 'static', title: _t('Static map') },
    { name: 'worldmap', title: _t('Geo Map') },
    { name: 'flow', title: _t('Flow Map') },
    { name: 'radar', title: _t('Radar (dynamic filter)') }
  ]
  if (includeFolderTree) {
    options.push({
      name: 'foldertree',
      title: `${_t('Folder tree')} (experimental)`
    })
  }
  if (includePresentation) {
    options.push({
      name: 'presentation',
      title: `${_t('Presentation')} (experimental)`
    })
  }
  return options
}

export function lineStyleOptions(_t: TranslateFn): { name: string | null; title: string }[] {
  const store = useObjectOptionsStore()
  const source = store.lineStyles.length > 0 ? store.lineStyles : LINE_STYLE_FALLBACK
  const titles = lineStyleTitles(_t)
  return [
    { name: null, title: _t('Default') },
    ...source.map((s) => {
      const title = titles[s.name]
      return { name: s.name, title: title ?? s.title }
    })
  ]
}

export function linePerfdataLabelOptions(_t: TranslateFn) {
  return [
    { name: 'none', title: _t('None') },
    { name: 'percent', title: _t('Percent') },
    { name: 'bandwidth', title: _t('Bandwidth') },
    { name: 'both', title: _t('Both') }
  ]
}
