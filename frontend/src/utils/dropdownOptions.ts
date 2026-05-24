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

export function placeableObjectTypes(t: T): { name: ObjectType; title: string }[] {
    return [
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
        { name: 'graph', title: `${t('boardSettings.typeGraph')} (experimental)` },
    ];
}

export function boardTypeOptions(t: T) {
    return [
        { name: 'static', title: t('board.boardTypeStatic') },
        { name: 'worldmap', title: t('board.boardTypeGeoBoard') },
        { name: 'flow', title: t('board.boardTypeFlowBoard') },
        { name: 'radar', title: t('board.boardTypeRadar') },
    ];
}

export function lineStyleOptions(t: T): { name: string | null; title: string }[] {
    const store = useObjectOptionsStore();
    const source = store.lineStyles.length > 0 ? store.lineStyles : LINE_STYLE_FALLBACK;
    return [
        { name: null, title: t('boardSettings.lineDefault') },
        ...source.map((s) => ({
            name: s.name,
            title: LINE_STYLE_I18N[s.name] ? t(LINE_STYLE_I18N[s.name]) : s.title,
        })),
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
