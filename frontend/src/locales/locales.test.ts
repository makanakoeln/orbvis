import { describe, expect, it } from 'vitest';

import deMessages from './de';
import enMessages from './en';

type LocaleNode = { [key: string]: string | LocaleNode };

function collectLeafPaths(obj: LocaleNode, prefix = ''): Map<string, string> {
    const result = new Map<string, string>();
    for (const [key, value] of Object.entries(obj)) {
        const path = prefix ? `${prefix}.${key}` : key;
        if (typeof value === 'string') {
            result.set(path, value);
        } else {
            for (const [subPath, subValue] of collectLeafPaths(value, path)) {
                result.set(subPath, subValue);
            }
        }
    }
    return result;
}

function extractInterpolationVars(value: string): Set<string> {
    const vars = new Set<string>();
    for (const [, name] of value.matchAll(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g)) {
        if (name !== undefined) vars.add(name);
    }
    return vars;
}

const enPaths = collectLeafPaths(enMessages as LocaleNode);
const dePaths = collectLeafPaths(deMessages as LocaleNode);

describe('locale key completeness', () => {
    it('every key in EN exists in DE', () => {
        const missing = [...enPaths.keys()].filter((k) => !dePaths.has(k));
        expect(missing).toEqual([]);
    });

    it('every key in DE exists in EN', () => {
        const missing = [...dePaths.keys()].filter((k) => !enPaths.has(k));
        expect(missing).toEqual([]);
    });
});

describe('interpolation variable consistency', () => {
    it('every EN interpolation variable is present in the DE translation', () => {
        const failures: string[] = [];
        for (const [path, enValue] of enPaths) {
            const enVars = extractInterpolationVars(enValue);
            if (enVars.size === 0) continue;
            const deValue = dePaths.get(path);
            if (deValue === undefined) continue;
            const deVars = extractInterpolationVars(deValue);
            for (const v of enVars) {
                if (!deVars.has(v)) {
                    failures.push(`${path}: EN has {${v}}, missing in DE ("${deValue}")`);
                }
            }
        }
        expect(failures).toEqual([]);
    });

    it('no extra interpolation variables appear in DE that are absent from EN', () => {
        const failures: string[] = [];
        for (const [path, deValue] of dePaths) {
            const deVars = extractInterpolationVars(deValue);
            if (deVars.size === 0) continue;
            const enValue = enPaths.get(path);
            if (enValue === undefined) continue;
            const enVars = extractInterpolationVars(enValue);
            for (const v of deVars) {
                if (!enVars.has(v)) {
                    failures.push(`${path}: DE has {${v}}, missing in EN ("${enValue}")`);
                }
            }
        }
        expect(failures).toEqual([]);
    });
});

describe('no empty string values', () => {
    it('EN has no empty string values', () => {
        const empty = [...enPaths.entries()].filter(([, v]) => v === '').map(([k]) => k);
        expect(empty).toEqual([]);
    });

    it('DE has no empty string values', () => {
        const empty = [...dePaths.entries()].filter(([, v]) => v === '').map(([k]) => k);
        expect(empty).toEqual([]);
    });
});

describe('top-level namespace symmetry', () => {
    it('both locales export the same top-level namespaces', () => {
        const enKeys = Object.keys(enMessages).sort();
        const deKeys = Object.keys(deMessages).sort();
        expect(deKeys).toEqual(enKeys);
    });
});
