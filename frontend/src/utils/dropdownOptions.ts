import type { ComposerTranslation } from 'vue-i18n';

import { useObjectOptionsStore } from '@/stores/objectOptions';
import type { ObjectType } from '@/types/api';

type T = ComposerTranslation;

// Maps backend ``name`` → frontend i18n key. The backend ships english
// titles too (used for FormSpec dropdowns where translations don't run),
// but the per-object EditPanel reads through this map so existing
// translations keep working. Unknown names fall back to the backend
// title — that means a new style added in the registry shows up
// immediately, just untranslated until someone adds a key here.
const LINE_STYLE_I18N: Record<string, string> = {
    plain: 'boardSettings.lineSimple',
    dashed: 'boardSettings.lineDashed',
    arrow_end: 'boardSettings.lineArrowRight',
    arrow_start: 'boardSettings.lineArrowLeft',
    arrow_both: 'boardSettings.lineDoubleArrow',
    arrow_inward: 'boardSettings.lineInward',
};

// Hard-coded list the very first paint uses — once the store has
// loaded (typically a few hundred ms after login) the registry takes
// over and any new styles surface here automatically.
const LINE_STYLE_FALLBACK: { name: string; title: string }[] = [
    { name: 'plain', title: 'Simple line' },
    { name: 'dashed', title: 'Dashed' },
    { name: 'arrow_end', title: 'Arrow at end' },
    { name: 'arrow_start', title: 'Arrow at start' },
    { name: 'arrow_both', title: 'Arrows on both ends' },
    { name: 'arrow_inward', title: 'Arrows pointing inward' },
];

// The graph object type is still experimental and opt-out via the System
// Settings feature flag (``includeGraph``, on by default). When off it's hidden
// from the add-object picker; existing graph objects keep rendering.
export function placeableObjectTypes(
    t: T,
    includeGraph = true,
): { name: ObjectType; title: string }[] {
    const types: { name: ObjectType; title: string }[] = [
        { name: 'host', title: t('boardSettings.typeHost') },
        { name: 'service', title: t('boardSettings.typeService') },
        { name: 'hostgroup', title: t('boardSettings.typeHostgroup') },
        { name: 'servicegroup', title: t('boardSettings.typeServicegroup') },
        { name: 'dyngroup', title: 'Dynamic group' },
        { name: 'map', title: t('boardSettings.typeMap') },
        { name: 'aggregation', title: t('boardSettings.typeAggregation') },
        { name: 'line', title: t('boardSettings.typeLine') },
        { name: 'textbox', title: t('boardSettings.typeTextbox') },
        { name: 'image', title: t('boardSettings.typeImage') },
    ];
    if (includeGraph) {
        types.push({ name: 'graph', title: `${t('boardSettings.typeGraph')} (experimental)` });
    }
    return types;
}

// The folder-tree board type is opt-in via the System Settings feature flag.
// ``includeFolderTree`` is the resolved flag; when off the type is hidden from
// the picker (existing folder boards still render). It stays listed when the
// board being edited is already a folder board, so its type isn't silently lost.
export function boardTypeOptions(t: T, includeFolderTree = false) {
    const options = [
        { name: 'static', title: t('board.boardTypeStatic') },
        { name: 'worldmap', title: t('board.boardTypeGeoBoard') },
        { name: 'flow', title: t('board.boardTypeFlowBoard') },
        { name: 'radar', title: t('board.boardTypeRadar') },
    ];
    if (includeFolderTree) {
        options.push({
            name: 'foldertree',
            title: `${t('board.boardTypeFolderTree')} (experimental)`,
        });
    }
    return options;
}

export function lineStyleOptions(t: T): { name: string | null; title: string }[] {
    const store = useObjectOptionsStore();
    const source = store.lineStyles.length > 0 ? store.lineStyles : LINE_STYLE_FALLBACK;
    return [
        { name: null, title: t('boardSettings.lineDefault') },
        ...source.map((s) => {
            const i18nKey = LINE_STYLE_I18N[s.name];
            return { name: s.name, title: i18nKey ? t(i18nKey) : s.title };
        }),
    ];
}

export function linePerfdataLabelOptions(t: T) {
    return [
        { name: 'none', title: t('boardSettings.linePerfdataNone') },
        { name: 'percent', title: t('boardSettings.linePerfdataPercent') },
        { name: 'bandwidth', title: t('boardSettings.linePerfdataBandwidth') },
        { name: 'both', title: t('boardSettings.linePerfdataBoth') },
    ];
}
