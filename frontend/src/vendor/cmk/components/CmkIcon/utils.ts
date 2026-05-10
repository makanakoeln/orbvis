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

// Builds an absolute "/<site>/check_mk/" prefix at runtime. Example:
//   page at /ZWEIFUENF/orbvis/#/boards/foo → '/ZWEIFUENF/check_mk/'
// We deliberately read window.location.pathname (not import.meta.env.BASE_URL)
// because the bundle is built with `base: './'` so it can be served from any
// OMD-site prefix without rebuilding. With a relative BASE_URL the icon path
// would otherwise resolve against the current SPA route (e.g. /<site>/orbvis/
// rather than /<site>/check_mk/) and 404.
//
// Falls back to '/check_mk/' when no '/orbvis/' segment is detected — that
// path resolves wherever OrbVis is co-deployed with a Checkmk site under the
// document root, which matches the current rollout.
function checkmkBase(): string {
    if (typeof window === 'undefined') return '/check_mk/';
    const pathname = window.location.pathname;
    const orbvisIdx = pathname.indexOf('/orbvis/');
    if (orbvisIdx >= 0) return `${pathname.slice(0, orbvisIdx)}/check_mk/`;
    return '/check_mk/';
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
