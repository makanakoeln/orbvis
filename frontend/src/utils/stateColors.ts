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
};

// Tailwind blue-500 / amber-400 — kept in sync with the badges rendered
// directly via Tailwind classes in BoardObject.vue (downtime/ack indicators).
export const DOWNTIME_COLOR = '#3b82f6';
export const ACKNOWLEDGED_COLOR = '#fbbf24';

export function stateColor(state: string | undefined): string {
    return STATE_COLORS[state ?? 'PENDING'] ?? STATE_COLORS['PENDING'];
}
