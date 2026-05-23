import type { BoardObject } from '@/types/api';

/**
 * Quicksearch tokens — mirror Checkmk's monitoring quicksearch prefixes so
 * operators can be selective without learning new syntax.
 *
 *   h:srv     host_name contains "srv"
 *   s:cpu     service_description contains "cpu"
 *   hg:linux  host group name contains "linux"
 *   sg:db     service group name contains "db"
 *   id:foo    object id contains "foo"
 *
 * Bare tokens (no prefix) match any of the searchable fields, preserving the
 * previous substring-anywhere behavior. Multiple space-separated tokens are
 * AND-combined.
 */

export type FilterField = 'host' | 'service' | 'hostgroup' | 'servicegroup' | 'id' | 'any';

const PREFIX_MAP: Record<string, FilterField> = {
    h: 'host',
    s: 'service',
    hg: 'hostgroup',
    sg: 'servicegroup',
    id: 'id',
};

export interface FilterTerm {
    field: FilterField;
    needle: string;
}

const PREFIX_KEYS = Object.keys(PREFIX_MAP).join('|');
const PREFIX_WS_RE = new RegExp(`(^|\\s)(${PREFIX_KEYS}):\\s+(?=\\S)`, 'g');

export function parseFilterTerms(query: string): FilterTerm[] {
    const terms: FilterTerm[] = [];
    const normalized = query.trim().toLowerCase().replace(PREFIX_WS_RE, '$1$2:');
    for (const raw of normalized.split(/\s+/)) {
        if (!raw) continue;
        const colon = raw.indexOf(':');
        if (colon > 0) {
            const prefix = raw.slice(0, colon);
            const value = raw.slice(colon + 1);
            const field = PREFIX_MAP[prefix];
            if (field && value) {
                terms.push({ field, needle: value });
                continue;
            }
        }
        terms.push({ field: 'any', needle: raw });
    }
    return terms;
}

/**
 * Generic matcher: the caller supplies a resolver mapping a FilterField to the
 * string values that should be searched on the underlying entity. Sharing this
 * keeps Static/Geo/Flow/Radar quicksearch behavior in sync.
 */
export function matchesFilterTerms(
    terms: FilterTerm[],
    getValues: (field: FilterField) => string[],
): boolean {
    if (terms.length === 0) return true;
    return terms.every(({ field, needle }) =>
        getValues(field).some((v) => v.toLowerCase().includes(needle)),
    );
}

function boardObjectFieldValue(obj: BoardObject, field: FilterField): string[] {
    switch (field) {
        case 'host':
            return [obj.host_name ?? ''];
        case 'service':
            return [obj.service_description ?? ''];
        case 'hostgroup':
            return obj.type === 'hostgroup' ? [obj.group_name ?? ''] : [];
        case 'servicegroup':
            return obj.type === 'servicegroup' ? [obj.group_name ?? ''] : [];
        case 'id':
            return [obj.id];
        case 'any':
            return [
                obj.id,
                obj.host_name ?? '',
                obj.service_description ?? '',
                obj.group_name ?? '',
                obj.aggregation_id ?? '',
                obj.map_name ?? '',
                obj.label?.text ?? '',
            ];
    }
}

export function objectMatchesFilter(obj: BoardObject, query: string): boolean {
    const terms = parseFilterTerms(query);
    return matchesFilterTerms(terms, (field) => boardObjectFieldValue(obj, field));
}
