import type { ComposerTranslation } from 'vue-i18n';

type T = ComposerTranslation;

export function boardTypeOptions(t: T) {
    return [
        { name: 'static', title: t('board.boardTypeStatic') },
        { name: 'worldmap', title: t('board.boardTypeGeoBoard') },
        { name: 'flow', title: t('board.boardTypeFlowBoard') },
        { name: 'radar', title: t('board.boardTypeRadar') },
    ];
}

export function lineStyleOptions(t: T) {
    return [
        { name: null, title: t('boardSettings.lineDefault') },
        { name: 'plain', title: t('boardSettings.lineSimple') },
        { name: 'arrow_end', title: t('boardSettings.lineArrowRight') },
        { name: 'arrow_start', title: t('boardSettings.lineArrowLeft') },
        { name: 'arrow_both', title: t('boardSettings.lineDoubleArrow') },
        { name: 'arrow_inward', title: t('boardSettings.lineInward') },
        { name: 'dashed', title: t('boardSettings.lineDashed') },
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
