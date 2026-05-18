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

type Field = 'host' | 'service' | 'hostgroup' | 'servicegroup' | 'id' | 'any';

const PREFIX_MAP: Record<string, Field> = {
    h: 'host',
    s: 'service',
    hg: 'hostgroup',
    sg: 'servicegroup',
    id: 'id',
};

interface Term {
    field: Field;
    needle: string;
}

function parseTerms(query: string): Term[] {
    const terms: Term[] = [];
    for (const raw of query.trim().toLowerCase().split(/\s+/)) {
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

function fieldValue(obj: BoardObject, field: Field): string[] {
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
    const terms = parseTerms(query);
    if (terms.length === 0) return true;
    return terms.every(({ field, needle }) =>
        fieldValue(obj, field).some((v) => v.toLowerCase().includes(needle)),
    );
}
