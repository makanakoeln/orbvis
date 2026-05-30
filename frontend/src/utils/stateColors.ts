/**
 * Kanonische Zustandsfarben — eine Quelle für BoardLine, WorldMapCanvas und BoardObject.
 * SVG-Attribute können kein var() nutzen, daher bleiben die Hex-Werte hier als JS-Map.
 * Die CSS-Vars in style.css (--color-warning etc.) müssen mit diesen Werten übereinstimmen.
 */
export const STATE_COLORS: Record<string, string> = {
    UP: '#4ade80',
    OK: '#4ade80',
    DOWN: '#f87171',
    CRITICAL: '#f87171',
    UNREACHABLE: '#fb923c',
    UNKNOWN: '#fb923c',
    WARNING: '#ffd000',
    PENDING: '#9ca3af',
    // Object referenced on the board doesn't exist in monitoring data — neutral
    // dim grey, paired with a dashed outline + "?" badge for clear differentiation.
    NOT_FOUND: '#71717a',
};

// Tailwind blue-500 / amber-400 — kept in sync with the badges rendered
// directly via Tailwind classes in BoardObject.vue (downtime/ack indicators).
export const DOWNTIME_COLOR = '#3b82f6';
export const ACKNOWLEDGED_COLOR = '#fbbf24';

export function stateColor(state: string | undefined): string {
    return STATE_COLORS[state ?? 'PENDING'] ?? STATE_COLORS['PENDING'];
}

// Display severity (worst first) — mirrors backend _COMBINED_SEVERITY ranking.
const SEVERITY_ORDER: Record<string, number> = {
    CRITICAL: 5,
    DOWN: 4,
    UNKNOWN: 3,
    UNREACHABLE: 3,
    WARNING: 2,
};

// States whose colour is light enough to need dark text on a filled badge.
const LIGHT_STATES = new Set(['WARNING']);

export interface SeverityPill {
    state: string;
    count: number;
    bg: string;
    fg: string;
}

/** Turn a folder's ``severity_counts`` into ordered, coloured badge pills
 *  (worst severity first). Only problem states appear in the input. */
export function severityPills(counts: Record<string, number> | undefined): SeverityPill[] {
    if (!counts) return [];
    return Object.entries(counts)
        .filter(([, n]) => n > 0)
        .sort((a, b) => (SEVERITY_ORDER[b[0]] ?? 1) - (SEVERITY_ORDER[a[0]] ?? 1))
        .map(([state, count]) => ({
            state,
            count,
            bg: stateColor(state),
            fg: LIGHT_STATES.has(state) ? '#1a1a1a' : '#ffffff',
        }));
}
