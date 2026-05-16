import type { AggregationNode, MonitoringState } from '@/types/api';

export type BiStateCode = 0 | 1 | 2 | 3;

export const BI_STATE_LABEL: Record<number, string> = {
    0: 'OK',
    1: 'WARN',
    2: 'CRIT',
    3: 'UNKN',
};

// Same codes mapped to MonitoringState names — used where BI nodes mix with
// host/service state-color lookups (stateColor() expects "OK"/"WARNING"/...).
export const BI_STATE_FULL_LABEL: Record<number, MonitoringState> = {
    0: 'OK',
    1: 'WARNING',
    2: 'CRITICAL',
    3: 'UNKNOWN',
};

export const BI_STATE_TONE: Record<number, 'ok' | 'warn' | 'crit' | 'unknown'> = {
    0: 'ok',
    1: 'warn',
    2: 'crit',
    3: 'unknown',
};

// CSS-var-backed colours used by the BI live preview and the BI tree.
// `_color-yellow` defaults stay aligned with the WARNING swatch from
// states.ts (#ffd000) so the preview matches the rest of the UI.
export const BI_STATE_COLOR: Record<number, string> = {
    0: 'var(--color-green, #22c55e)',
    1: 'var(--color-yellow, #ffd000)',
    2: 'var(--color-red, #ef4444)',
    3: 'var(--color-orange, #f97316)',
};

export function flattenAggregationLeaves(
    node: AggregationNode,
    out: AggregationNode[] = [],
): AggregationNode[] {
    if (node.node_type === 'bi_leaf') {
        out.push(node);
    } else {
        for (const child of node.children) flattenAggregationLeaves(child, out);
    }
    return out;
}

export interface AggregationLeafWithPath {
    leaf: AggregationNode;
    path: string[];
}

export function walkAggregationLeavesWithPath(
    node: AggregationNode,
    path: string[] = [],
): AggregationLeafWithPath[] {
    if (node.node_type === 'bi_leaf') {
        return [{ leaf: node, path: [...path, node.name] }];
    }
    const out: AggregationLeafWithPath[] = [];
    const sub = [...path, node.name];
    for (const child of node.children) {
        out.push(...walkAggregationLeavesWithPath(child, sub));
    }
    return out;
}

// Stable identifier for a leaf, matching the (host, service) shape the
// detail drawer + bulk-ack paths use. Falls back to the leaf's `name`
// for synthetic / placeholder leaves that carry neither.
export function aggregationLeafId(leaf: AggregationNode): string {
    if (leaf.service_description) {
        return `${leaf.host_name ?? ''};${leaf.service_description}`;
    }
    return leaf.host_name ?? leaf.name;
}

export function countLeavesByState(leaves: AggregationNode[]): Record<number, number> {
    const counts: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 };
    for (const l of leaves) counts[l.state] = (counts[l.state] ?? 0) + 1;
    return counts;
}
