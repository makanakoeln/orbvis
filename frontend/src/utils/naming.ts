import type { BoardObject, ObjectType } from '@/types/api';

/** Object types that are purely decorative and carry no monitoring state. */
export const VISUAL_ONLY_TYPES: readonly ObjectType[] = ['image', 'textbox', 'line'];

/**
 * Return a human-readable type label for a board object.
 * Graph and line objects are labelled by what they monitor ('service' or 'host')
 * when linked to one, not by their OrbVis object type.
 */
export function getObjectTypeLabel(object: BoardObject): string {
    if (object.type === 'graph' || object.type === 'line') {
        if (object.service_description) return 'service';
        if (object.host_name) return 'host';
    }
    return object.type;
}

/** Return the display name for a board object (label > host/service > host/group/map/aggregation > id). */
export function getBoardObjectName(object: BoardObject): string {
    if (object.label?.text) return object.label.text;
    return getBoardObjectIdentifier(object);
}

/** Raw monitoring identifier, ignoring the custom `label.text` override. */
export function getBoardObjectIdentifier(object: BoardObject): string {
    if (object.host_name && object.service_description)
        return `${object.host_name} / ${object.service_description}`;
    return (
        object.host_name ??
        object.group_name ??
        object.map_name ??
        object.aggregation_id ??
        object.id
    );
}

/** Sanitize a raw string into a valid board ID: spaces → hyphens, strip invalid chars. */
export function sanitizeBoardName(raw: string): string {
    return raw.replace(/ /g, '-').replace(/[^a-zA-Z0-9_-]/g, '');
}

/** Convert a hyphen/underscore-separated slug to Title Case display name. */
export function slugToTitleCase(slug: string): string {
    return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
