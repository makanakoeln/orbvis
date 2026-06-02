const PROBLEM_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);

export function isProblemState(state: string | null | undefined): boolean {
    return state != null && PROBLEM_STATES.has(state);
}

// Decorative types (textbox/image/line/map/cmk_label/graph) carry no state and
// stay visible under the problems-only filter; only these types are filtered.
export const STATEFUL_OBJECT_TYPES = new Set([
    'host',
    'service',
    'hostgroup',
    'servicegroup',
    'dyngroup',
    'aggregation',
    'site',
]);
