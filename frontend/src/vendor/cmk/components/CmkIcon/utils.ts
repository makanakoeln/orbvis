/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 *
 * OrbVis-specific patch: getIconPath returns a runtime URL instead of relying
 * on the Vite asset graph. The icons live in the sibling Checkmk site under
 * `<base>/check_mk/themes/...` and are resolved at request time, so the bundle
 * stays free of binary asset deps.
 */
import { iconSizes, themedIcons, unthemedIcons } from './icons.constants';
import { type IconSizeNames, type SimpleIcons } from './types';

export function iconSizeNametoNumber(sizeName: IconSizeNames | undefined) {
    let size;
    if (sizeName === undefined) {
        size = iconSizes['medium'];
    } else {
        size = iconSizes[sizeName];
    }
    return size;
}

// Builds "<base>/check_mk/" relative to the bundle's BASE_URL. Example:
//   BASE_URL '/ZWEIFUENF/orbvis/' → '/ZWEIFUENF/check_mk/'
// In standalone mode (BASE_URL '/') this becomes '/check_mk/'; that path only
// resolves when OrbVis is co-deployed with a Checkmk site, which matches the
// current rollout.
function checkmkBase(): string {
    const base = import.meta.env.BASE_URL || '/';
    // Replace trailing /orbvis/ with /check_mk/ when present, otherwise sit at /check_mk/.
    if (base.endsWith('/orbvis/')) return base.replace(/\/orbvis\/$/, '/check_mk/');
    if (base.endsWith('/')) return `${base}check_mk/`;
    return `${base}/check_mk/`;
}

export function getIconPath(name: SimpleIcons, theme: string): string {
    let internalTheme = 'dark';
    if (theme === 'facelift') {
        internalTheme = 'light';
    }

    const themedPath = themedIcons[internalTheme]?.[name];
    if (themedPath) {
        return `${checkmkBase()}${themedPath}`;
    }

    const unthemedPath = unthemedIcons[name];
    if (!unthemedPath) {
        return '';
    }

    return `${checkmkBase()}${unthemedPath}`;
}
