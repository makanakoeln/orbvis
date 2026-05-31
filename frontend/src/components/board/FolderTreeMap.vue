<template>
    <div class="ftm">
        <div v-if="!root" class="ftm-placeholder">Waiting for folder data…</div>
        <template v-else>
            <div v-if="!preview" class="ftm-bar">
                <button type="button" class="ftm-btn" @click="expandAll">Expand all</button>
                <button type="button" class="ftm-btn" @click="collapseAll">Collapse all</button>
            </div>
            <div ref="hostEl" class="ftm-stage">
                <svg ref="svgEl" class="ftm-svg" />
                <div v-if="tip" class="ftm-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
                    <span class="ftm-tip-dot" :style="{ background: tip.color }" />
                    <strong>{{ tip.title }}</strong>
                    <span class="ftm-tip-meta">{{ tip.meta }}</span>
                </div>
                <div v-if="empty" class="ftm-placeholder ftm-placeholder--overlay">
                    Nothing to show here.
                </div>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import {
    type BaseType,
    hierarchy,
    type HierarchyRectangularNode,
    select,
    type Selection,
    treemap,
    treemapSquarify,
} from 'd3';
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';

import { useStatesStore } from '@/stores/states';
import type { FolderTreeNode } from '@/types/api';
import { severityPills, stateColorVar, stateRank } from '@/utils/stateColors';

const props = defineProps<{
    problemsOnly: boolean;
    preview?: boolean;
    showServices: boolean;
    servicesByHost: Record<string, FolderTreeNode[]>;
    serviceLoading: Set<string>;
    serviceError: Set<string>;
}>();
const emit = defineEmits<{
    'select-host': [FolderTreeNode];
    'select-service': [string, FolderTreeNode];
    'expand-host': [FolderTreeNode];
}>();

const states = useStatesStore();
const root = computed<FolderTreeNode | null>(() => states.folderTree);

const svgEl = ref<SVGSVGElement | null>(null);
const hostEl = ref<HTMLDivElement | null>(null);

type FNode = HierarchyRectangularNode<FolderTreeNode>;

const HEADER = 19; // expanded-folder title bar height
const PROBLEM = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);
const isProblem = (n: FolderTreeNode) => PROBLEM.has(n.state);

const tip = ref<{ x: number; y: number; title: string; meta: string; color: string } | null>(null);
const empty = ref(false);

// Folders start collapsed (shown as solid status tiles); the operator expands
// them in place, just like the List view. Path-keyed so it survives relayout.
const expanded = reactive(new Set<string>());

let lastSig = '';
let dims = { w: 0, h: 0 };
let resizeObs: ResizeObserver | null = null;

function prune(node: FolderTreeNode): FolderTreeNode | null {
    if (node.kind === 'host') return isProblem(node) ? node : null;
    const kids = node.children.map(prune).filter((c): c is FolderTreeNode => c !== null);
    if (!kids.length && !isProblem(node)) return null;
    return { ...node, children: kids };
}

function currentRoot(): FolderTreeNode {
    if (!root.value) return { path: '', title: '', kind: 'folder' } as FolderTreeNode;
    if (!props.problemsOnly) return root.value;
    return prune(root.value) ?? { ...root.value, children: [] };
}

// A node the operator can drill into: a non-empty folder, or — when
// show_services is on — a host (drills to its lazily-loaded services).
const canExpand = (n: FolderTreeNode): boolean =>
    n.kind === 'folder' ? !n.is_empty : n.kind === 'host' && props.showServices;
// Mirror the List's problems-only filtering of service leaves so both views of
// the same board show the same set (prune() only covers folders/hosts).
const hostServices = (n: FolderTreeNode): FolderTreeNode[] => {
    const svcs = props.servicesByHost[n.title] ?? [];
    return props.problemsOnly ? svcs.filter((s) => isProblem(s)) : svcs;
};

// Laid-out node that actually has children rendered inside it (folder or host
// expanded to its services).
const isExpanded = (d: FNode) => (d.children?.length ?? 0) > 0;

// Visual language: containers (folders, expanded hosts) read as faint framed
// cards with a header tab; leaves (collapsed hosts, services) read as solid
// status chips. So a collapsed folder never looks like a host (the recurring
// confusion) — folders are always framed, hosts/services are always solid.
const isContainerCell = (d: FNode): boolean =>
    (d.data.kind === 'folder' && !d.data.is_empty) || (d.data.kind === 'host' && isExpanded(d));

function fillFor(d: FNode): string {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 'transparent';
    if (isContainerCell(d)) return isProblem(n) ? stateColorVar(n.state) : 'var(--bg-surface)';
    return stateColorVar(n.state); // host chip or service chip → solid status tile
}

function fillOpacityFor(d: FNode): number {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 1;
    if (isContainerCell(d)) return isProblem(n) ? 0.16 : 0.05; // faint framed backdrop
    return isProblem(n) ? 1 : 0.4; // healthy chips recede, problems dominate
}

function strokeFor(d: FNode): string {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 'var(--text-muted)';
    // Containers carry a status-colored frame so a problem still pops despite the
    // faint body; healthy containers get a neutral border.
    if (isContainerCell(d)) return isProblem(n) ? stateColorVar(n.state) : 'var(--border)';
    return 'var(--border)';
}

function strokeWidthFor(d: FNode): number {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 1.4;
    if (isContainerCell(d) && isProblem(n)) return 2; // colored frame on a problem container
    return 1;
}

function folderLabel(n: FolderTreeNode): string {
    const title = n.title || 'Main';
    if (n.is_empty) return `${title} · empty`;
    const pills = severityPills(n.severity_counts);
    if (pills.length) return `${title} · ${pills[0].count} ${pills[0].state}`;
    return `${title} · ${n.host_count}`;
}

// A container cell shows a header band with a chevron + label. Folders are
// framed even when collapsed; a host only grows a header once expanded (its
// collapsed form stays a chip, with a chevron prefix to signal it can expand).
const hasHeader = (d: FNode) => isContainerCell(d);

function labelText(d: FNode): string {
    const n = d.data;
    if (hasHeader(d)) {
        const chev = isExpanded(d) ? '▾ ' : '▸ ';
        return n.kind === 'folder' ? `${chev}${folderLabel(n)}` : `${chev}${n.title}`;
    }
    if (n.kind === 'folder') return folderLabel(n); // empty folder
    // Collapsed host that can drill into services → chevron hints expandability.
    if (n.kind === 'host' && canExpand(n)) return `▸ ${n.title}`;
    return n.title; // plain host or service chip
}

// Approx glyph advance at 12px/600 — used to clip labels to their tile so long
// service names ellipsize instead of bleeding out of the box (full name on hover).
const CHAR_W = 7;
function fitLabel(text: string, width: number): string {
    const max = Math.floor((width - 12) / CHAR_W);
    if (max <= 1) return '';
    if (text.length <= max) return text;
    return text.slice(0, Math.max(1, max - 1)).trimEnd() + '…';
}

// Command-state glyphs shown in a tile corner (mirrors the List's ✔/⏸ markers)
// so acknowledged / in-downtime hosts and services are recognisable in the map.
function markText(n: FolderTreeNode): string {
    return (n.acknowledged ? '✔' : '') + (n.in_downtime ? '⏸' : '');
}

function allFolderPaths(node: FolderTreeNode, acc: string[] = []): string[] {
    if (node.kind === 'folder') {
        if (node.path) acc.push(node.path);
        node.children.forEach((c) => allFolderPaths(c, acc));
    }
    return acc;
}

function layout(): FNode | null {
    if (!dims.w || !dims.h) return null;
    const rootData = currentRoot();
    // A host is "open" only once its services have actually loaded — until then
    // it stays a chip (and the click that opened it triggered the lazy fetch).
    const isOpen = (d: FolderTreeNode) => {
        if (d.kind === 'folder') return d.children.length > 0 && expanded.has(d.path);
        if (d.kind === 'host')
            return props.showServices && expanded.has(d.path) && hostServices(d).length > 0;
        return false;
    };
    const childrenOf = (d: FolderTreeNode) => (d.kind === 'host' ? hostServices(d) : d.children);
    const h = hierarchy<FolderTreeNode>(rootData, (d) => (isOpen(d) ? childrenOf(d) : undefined))
        // Tile weights: a folder reads as a slightly larger card than a single
        // host (container vs. leaf) without host-count dwarfing the map; empty
        // folders smallest; services size like hosts. Open nodes contribute 0 and
        // grow to their children.
        .sum((d) =>
            d.kind === 'service'
                ? 1
                : d.kind === 'host'
                  ? isOpen(d)
                      ? 0
                      : 1
                  : isOpen(d)
                    ? 0
                    : d.is_empty
                      ? 0.5
                      : 2,
        )
        // Mirror the list order: a folder's own hosts before its subfolders,
        // then worst severity first (problems cluster top-left), then bigger.
        .sort(
            (a, b) =>
                (a.data.kind === 'folder' ? 1 : 0) - (b.data.kind === 'folder' ? 1 : 0) ||
                stateRank(b.data.state) - stateRank(a.data.state) ||
                (b.value ?? 0) - (a.value ?? 0),
        );
    return treemap<FolderTreeNode>()
        .tile(treemapSquarify.ratio(1))
        .size([dims.w, dims.h])
        .paddingOuter(3)
        .paddingTop((d) => (d.children ? HEADER : 0))
        .paddingInner(3)
        .round(true)(h);
}

function visibleSig(node: FNode): string {
    return node
        .descendants()
        .map((d) => d.data.path)
        .join('|');
}

function toggleFolder(path: string): void {
    if (expanded.has(path)) expanded.delete(path);
    else expanded.add(path);
    draw(true);
}

function expandAll(): void {
    const r = currentRoot();
    expanded.add(r.path);
    allFolderPaths(r).forEach((p) => expanded.add(p));
    draw(true);
}

function collapseAll(): void {
    // Keep Main open so the result is the top-level overview, not a single tile.
    expanded.clear();
    expanded.add(currentRoot().path);
    draw(true);
}

function showTip(event: MouseEvent, d: FNode): void {
    if (!hostEl.value) return;
    const rect = hostEl.value.getBoundingClientRect();
    const n = d.data;
    const pills = severityPills(n.severity_counts);
    const breakdown = pills.length
        ? pills.map((p) => `${p.count} ${p.state}`).join(' · ')
        : 'all OK';
    const flags = [n.acknowledged ? 'ACK' : '', n.in_downtime ? 'DOWNTIME' : '']
        .filter(Boolean)
        .join(' · ');
    const base =
        n.kind === 'host' || n.kind === 'service'
            ? n.state
            : n.is_empty
              ? 'empty · 0 hosts'
              : `${n.host_count} hosts · ${breakdown}`;
    const meta = flags ? `${base} · ${flags}` : base;
    tip.value = {
        x: event.clientX - rect.left + 12,
        y: event.clientY - rect.top + 12,
        title: n.title,
        meta,
        color: n.is_empty ? 'var(--text-muted)' : stateColorVar(n.state),
    };
}

function draw(animate: boolean): void {
    if (!svgEl.value) return;
    const laid = layout();
    if (!laid) return;
    lastSig = visibleSig(laid);
    // Render the Main root too — as an outer container with a "Main" header — so
    // it is clear that the loose top-level host tiles are Main's direct hosts.
    const nodes = laid.descendants();
    // "Empty" = the data root truly has no folders/hosts — NOT merely a collapsed
    // Main (whose layout node then has no children). Otherwise the overlay would
    // cover the single Main tile and swallow the click that re-expands it.
    empty.value = currentRoot().children.length === 0;

    const svg = select(svgEl.value).attr('viewBox', `0 0 ${dims.w} ${dims.h}`);
    let g = svg.select<SVGGElement>('g.ftm-cells');
    if (g.empty()) g = svg.append('g').attr('class', 'ftm-cells');

    const dur = animate ? 450 : 0;

    const cells = g
        .selectAll<SVGGElement, FNode>('g.ftm-cell')
        .data(nodes, (d) => d.data.path + ':' + d.data.kind);

    cells.exit().transition().duration(dur).style('opacity', 0).remove();

    const enter = cells
        .enter()
        .append('g')
        .attr('class', 'ftm-cell')
        .style('opacity', 0)
        .attr('transform', (d) => `translate(${d.x0},${d.y0})`);
    enter.append('rect').attr('class', 'ftm-body');
    enter.append('rect').attr('class', 'ftm-hdr');
    enter.append('text').attr('class', 'ftm-label');
    enter.append('text').attr('class', 'ftm-mark');

    const merged = enter.merge(cells);
    merged
        .style('cursor', 'pointer')
        .on('click', (event: MouseEvent, d) => {
            event.stopPropagation();
            const n = d.data;
            if (canExpand(n)) {
                // Drilling a host triggers its lazy service fetch; the relayout
                // follows once servicesByHost updates (watched below).
                if (n.kind === 'host') emit('expand-host', n);
                toggleFolder(n.path);
            } else if (n.kind === 'host') {
                emit('select-host', n);
            } else if (n.kind === 'service') {
                emit('select-service', d.parent?.data.title ?? '', n);
            }
        })
        .on('mousemove', showTip)
        .on('mouseleave', () => (tip.value = null));
    merged
        .transition()
        .duration(dur)
        .style('opacity', 1)
        .attr('transform', (d) => `translate(${d.x0},${d.y0})`);

    merged
        .select('rect.ftm-body')
        .attr('rx', 3)
        .attr('stroke-width', strokeWidthFor)
        .attr('stroke-dasharray', (d) =>
            d.data.kind === 'folder' && d.data.is_empty ? '4 3' : null,
        )
        // fill/stroke via CSS style so the CMK `var(--color-state-*)` resolve
        // (SVG presentation attributes can't); geometry/opacity still animate.
        .style('fill', fillFor)
        .style('stroke', strokeFor)
        .transition()
        .duration(dur)
        .attr('width', (d) => Math.max(0, d.x1 - d.x0))
        .attr('height', (d) => Math.max(0, d.y1 - d.y0))
        .attr('fill-opacity', fillOpacityFor);

    // Folder header band (darkens the top strip into a "tab"); hidden for hosts
    // and empty folders.
    merged
        .select('rect.ftm-hdr')
        .attr('rx', 3)
        .attr('fill', 'black')
        .style('display', (d) => (hasHeader(d) ? null : 'none'))
        .transition()
        .duration(dur)
        .attr('width', (d) => Math.max(0, d.x1 - d.x0))
        .attr('height', (d) => Math.min(HEADER, Math.max(0, d.y1 - d.y0)))
        .attr('fill-opacity', 0.18);

    paintLabels(merged);
}

// Label + command-state marker rendering, shared by draw() and recolor() so a
// recolor pass doesn't clobber the marker text or drop label truncation.
function paintLabels(sel: Selection<SVGGElement, FNode, BaseType, unknown>): void {
    sel.select<SVGTextElement>('text.ftm-label').each(function (d) {
        const w = d.x1 - d.x0;
        const h = d.y1 - d.y0;
        const t = select(this);
        if (hasHeader(d)) {
            // Folder/expanded host: label sits in the header band next to the chevron.
            t.text(fitLabel(labelText(d), w))
                .attr('x', 6)
                .attr('y', 13)
                .attr('text-anchor', 'start')
                .style('display', w > 30 ? 'inline' : 'none');
        } else {
            // Host or service chip: centered, clipped to the tile so it never
            // overflows the box (full name available via the hover tooltip).
            t.text(fitLabel(labelText(d), w))
                .attr('x', w / 2)
                .attr('y', h / 2 + 4)
                .attr('text-anchor', 'middle')
                .style('display', w > 34 && h > 18 ? 'inline' : 'none');
        }
    });
    sel.select<SVGTextElement>('text.ftm-mark').each(function (d) {
        const w = d.x1 - d.x0;
        const h = d.y1 - d.y0;
        const m = markText(d.data);
        select(this)
            .text(m)
            .attr('x', w - 4)
            .attr('y', 13)
            .attr('text-anchor', 'end')
            .style('display', m && w > 28 && h > 16 ? 'inline' : 'none');
    });
}

// Recolor without relayout when only states changed (same visible set). Labels
// carry live severity counts, so refresh their text too.
function recolor(): void {
    if (!svgEl.value) return;
    const g = select(svgEl.value).select('g.ftm-cells');
    g.selectAll<SVGRectElement, FNode>('rect.ftm-body')
        .style('fill', fillFor)
        .style('stroke', strokeFor)
        .transition()
        .duration(400)
        .attr('fill-opacity', fillOpacityFor);
    paintLabels(g.selectAll<SVGGElement, FNode>('g.ftm-cell'));
}

// Open the Main root by default (once per root identity), but leave it
// collapsible — the operator can fold the whole tree into a single Main tile.
let seededFor = '';
watch(
    root,
    (r) => {
        if (!r) return;
        const sig = r.path + '|' + r.children.length;
        if (sig === seededFor) return;
        seededFor = sig;
        expanded.add(currentRoot().path);
    },
    { immediate: true },
);

// Re-lay out (or just recolor when the visible set is unchanged) on any input
// that affects the treemap: live tree, problems-only toggle, or lazily-loaded
// host services arriving / changing state (a freshly expanded host grows into
// its service tiles).
function relayout(): void {
    if (!root.value || !svgEl.value || !dims.w) return;
    const laid = layout();
    if (laid && visibleSig(laid) === lastSig) recolor();
    else draw(true);
}

watch(
    [
        root,
        () => props.problemsOnly,
        () =>
            Object.entries(props.servicesByHost)
                .map(
                    ([h, svcs]) =>
                        `${h}:${svcs.length}:${svcs
                            .map(
                                (s) =>
                                    s.state +
                                    (s.acknowledged ? 'a' : '') +
                                    (s.in_downtime ? 'd' : ''),
                            )
                            .join(',')}`,
                )
                .join('|'),
    ],
    relayout,
    { flush: 'post' },
);

onMounted(() => {
    if (!hostEl.value) return;
    resizeObs = new ResizeObserver((entries) => {
        const r = entries[0].contentRect;
        const changed = Math.abs(r.width - dims.w) > 1 || Math.abs(r.height - dims.h) > 1;
        dims = { w: r.width, h: r.height };
        if (changed && root.value) draw(false);
    });
    resizeObs.observe(hostEl.value);
});

onUnmounted(() => {
    resizeObs?.disconnect();
    if (svgEl.value) select(svgEl.value).selectAll('*').interrupt();
});
</script>

<style scoped>
.ftm {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

.ftm-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    font-size: 12px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.ftm-btn {
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
}

.ftm-btn:hover {
    background: var(--bg-hover);
}

.ftm-stage {
    position: relative;
    flex: 1;
    min-height: 0;
}

.ftm-svg {
    width: 100%;
    height: 100%;
    display: block;
}

.ftm-svg :deep(.ftm-label) {
    pointer-events: none;
    fill: var(--text);
    font-size: 12px;
    font-weight: 600;
    paint-order: stroke;
    stroke: var(--bg-glass);
    stroke-width: 2.5px;
    stroke-linejoin: round;
}

.ftm-svg :deep(.ftm-mark) {
    pointer-events: none;
    fill: var(--text);
    font-size: 11px;
    paint-order: stroke;
    stroke: var(--bg-glass);
    stroke-width: 2.5px;
    stroke-linejoin: round;
}

.ftm-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 13px;
    padding: 24px;
    text-align: center;
}

.ftm-placeholder--overlay {
    position: absolute;
    inset: 0;
    pointer-events: none; /* never swallow clicks on the tiles beneath */
}

.ftm-tip {
    position: absolute;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 5px 9px;
    border-radius: 6px;
    background: var(--bg-glass);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 12px;
    pointer-events: none;
    white-space: nowrap;
    box-shadow: 0 2px 10px rgb(0 0 0 / 18%);
}

.ftm-tip-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
}

.ftm-tip-meta {
    color: var(--text-muted);
}
</style>
