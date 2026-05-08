import type { BoardObject } from '@/types/api';

/**
 * Substring match for the operator-facing search bar — used by every board
 * type to dim or hide non-matching objects analogous to FlowBoard's filter.
 *
 * Empty needle → always true so callers can pass the raw input without a
 * separate "filter active" check.
 */
export function objectMatchesFilter(obj: BoardObject, needle: string): boolean {
    if (!needle) return true;
    const n = needle.trim().toLowerCase();
    if (!n) return true;
    const fields: (string | null | undefined)[] = [
        obj.id,
        obj.host_name,
        obj.service_description,
        obj.group_name,
        obj.aggregation_id,
        obj.map_name,
        obj.label?.text,
    ];
    return fields.some((f) => typeof f === 'string' && f.toLowerCase().includes(n));
}
