<template>
    <div class="absolute inset-0 bg-[var(--bg)]">
        <div v-if="loading" class="flex items-center justify-center h-full text-zinc-500 text-sm">
            Loading topology…
        </div>
        <div v-else-if="error" class="flex items-center justify-center h-full text-red-400 text-sm">
            {{ error }}
        </div>
        <svg v-else ref="svgEl" class="w-full h-full block" />

        <!-- Zoom controls -->
        <div
            v-if="!loading && !error"
            class="absolute bottom-4 left-4 z-10 flex flex-col overflow-hidden rounded-xl ring-1 ring-[var(--border)] shadow-xl shadow-black/40"
        >
            <button
                title="Zoom in"
                class="p-[5px] bg-[var(--bg-surface)]/90 backdrop-blur-md text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors border-b border-[var(--border)]"
                @click="zoomIn"
            >
                <svg
                    style="width: 14px; height: 14px"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 4.5v15m7.5-7.5h-15"
                    />
                </svg>
            </button>
            <button
                title="Fit all"
                class="p-[5px] bg-[var(--bg-surface)]/90 backdrop-blur-md text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors border-b border-[var(--border)]"
                @click="fitView"
            >
                <svg
                    style="width: 14px; height: 14px"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                    />
                </svg>
            </button>
            <button
                title="Zoom out"
                class="p-[5px] bg-[var(--bg-surface)]/90 backdrop-blur-md text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                @click="zoomOut"
            >
                <svg
                    style="width: 14px; height: 14px"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
                </svg>
            </button>
        </div>

        <!-- Hover popup -->
        <HoverMenu
            v-if="hoverMenu.visible && hoverMenu.object"
            :object="hoverMenu.object"
            :state="hoverMenu.state"
            :x="hoverMenu.x"
            :y="hoverMenu.y"
            :connection-id="props.connectionId"
        />
    </div>
</template>

<script setup lang="ts">
import {
    arc as d3arc,
    drag,
    forceCollide,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    pie as d3pie,
    select,
    type SimulationLinkDatum,
    type SimulationNodeDatum,
    zoom,
    zoomIdentity,
} from 'd3';
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue';

import { connectionsApi } from '@/api/client';
import HoverMenu from '@/components/board/HoverMenu.vue';
import { useD3Cleanup } from '@/composables/useD3Cleanup';
import { useAuthStore } from '@/stores/auth';
import type { BoardObject, ClickAction, FlowView, ObjectState, TopologyNode } from '@/types/api';
import { buildCheckmkUrl, openUrl } from '@/utils/boardNavigation';
import { stateColor } from '@/utils/stateColors';

const props = defineProps<{
    connectionId: string;
    serviceLayout: 'off' | 'fan' | 'row' | 'orbit' | 'donut';
    readonly?: boolean;
    clickAction?: ClickAction;
    checkmkUrl?: string | null;
    flowView?: FlowView | null;
}>();
const auth = useAuthStore();

const NODE_R = 18;
const SVC_R_MAX = 11; // service node radius at low service count
const ORBIT_R_MIN = 80; // minimum orbit/fan radius

// Scale service node radius down when a host has many services
function svcR(N: number): number {
    if (N <= 6) return SVC_R_MAX;
    if (N <= 12) return 9;
    if (N <= 20) return 7;
    return 6;
}

// Scale orbit radius up so service circles don't overlap.
// Full circle circumference = 2π·R must fit N circles of diameter 2r+gap.
function orbitR(N: number): number {
    const r = svcR(N);
    return Math.max(ORBIT_R_MIN, Math.ceil((N * (r * 2 + 3)) / (2 * Math.PI)));
}

// Fan = semicircle below host. Arc length = FAN_SPREAD·R must fit N service
// circles spaced 2r+gap apart, so the radius scales like ~2× orbitR for large N.
const FAN_SPREAD = Math.PI * 0.9;
function fanR(N: number): number {
    const r = svcR(N);
    if (N <= 1) return ORBIT_R_MIN;
    return Math.max(ORBIT_R_MIN, Math.ceil(((N - 1) * (r * 2 + 3)) / FAN_SPREAD));
}

function layoutR(N: number): number {
    return props.serviceLayout === 'fan' ? fanR(N) : orbitR(N);
}

// Show labels only when few enough services per host
function showSvcLabel(N: number): boolean {
    return N <= 10;
}

const MORE_NODE_MARKER = '__more__';

// Donut ring around a host: aggregated services_summary as proportional arcs.
// Inner radius sits a few px outside the host circle, outer adds the ring width.
const DONUT_INNER = NODE_R + 3;
const DONUT_OUTER = NODE_R + 11;
type DonutSegment = { state: 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING'; value: number };
const donutArc = d3arc<{ startAngle: number; endAngle: number }>()
    .innerRadius(DONUT_INNER)
    .outerRadius(DONUT_OUTER);
const donutPie = d3pie<DonutSegment>()
    .sort(null)
    .value((d) => d.value);

function donutSegments(n: TopologyNode): DonutSegment[] {
    const s = n.services_summary;
    if (!s) return [];
    // Order matters visually: critical first so it dominates the top of the ring.
    const all: DonutSegment[] = [
        { state: 'CRITICAL', value: s.critical },
        { state: 'WARNING', value: s.warning },
        { state: 'UNKNOWN', value: s.unknown },
        { state: 'PENDING', value: s.pending },
        { state: 'OK', value: s.ok },
    ];
    return all.filter((seg) => seg.value > 0);
}
const svgEl = ref<SVGSVGElement | null>(null);
useD3Cleanup(svgEl);
const nodes = ref<TopologyNode[]>([]);
const loading = ref(true);
const error = ref('');
const hoverMenu = reactive<{
    visible: boolean;
    object: BoardObject | null;
    state: ObjectState | undefined;
    x: number;
    y: number;
}>({ visible: false, object: null, state: undefined, x: 0, y: 0 });
let timer: ReturnType<typeof setInterval> | null = null;

// Layouts that need the full per-host service list. Donut renders only
// services_summary aggregates and therefore skips the bulk query entirely —
// that's the main scaling win for large installations.
function needsServices(layout: typeof props.serviceLayout): boolean {
    return layout === 'fan' || layout === 'orbit' || layout === 'row';
}

// ---- Fetch ----
async function fetchTopology() {
    try {
        nodes.value = await connectionsApi.topology(
            props.connectionId,
            auth.accessToken!,
            needsServices(props.serviceLayout),
            {
                root: props.flowView?.root ?? null,
                childLayers: props.flowView?.child_layers ?? null,
                parentLayers: props.flowView?.parent_layers ?? null,
            },
        );
    } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load topology';
    } finally {
        loading.value = false;
    }
}

// Re-fetch and clear service cache when serviceLayout prop changes
watch(
    () => props.serviceLayout,
    (newVal, oldVal) => {
        for (const k of nodeCache.keys()) {
            if (k.includes('::')) nodeCache.delete(k);
        }
        // When enabling services, reset host positions so the simulation can spread them out
        // from scratch rather than starting from a cramped no-service layout.
        if (newVal !== 'off' && oldVal === 'off') {
            for (const node of nodeCache.values()) {
                node.x = undefined;
                node.y = undefined;
                node.vx = undefined;
                node.vy = undefined;
            }
        }
        _hasFitOnce = false;
        fetchTopology();
    },
);

onMounted(() => {
    fetchTopology();
    timer = setInterval(fetchTopology, 15000);
});
onUnmounted(() => {
    if (timer) clearInterval(timer);
    simulation?.stop();
    if (svgEl.value) select(svgEl.value).selectAll('*').remove();
});

// ---- D3 force types ----
interface FNode extends SimulationNodeDatum {
    id: string;
    state: string;
    output: string;
    bfsLevel: number;
    nodeType: 'host' | 'service' | 'more';
    hostId?: string;
    svcTotalCount?: number; // total services for this host (set on service nodes for label visibility)
    moreCount?: number; // for nodeType='more': number of services hidden behind this aggregate
    // Cached pointer to the host's TopologyNode so the tooltip can show the
    // same status detail (alias, services_summary, …) as the static board.
    // Only set on host nodes; service nodes have minimal data via their parent.
    topo?: TopologyNode;
    // d3-force sets x/y/vx/vy
}
interface FLink extends SimulationLinkDatum<FNode> {
    source: FNode;
    target: FNode;
    sourceState: string;
    isServiceLink: boolean;
}

function boardObjectFromFNode(d: FNode): BoardObject {
    const isService = d.nodeType === 'service';
    const svcName = isService ? d.id.split('::').slice(1).join('::') : undefined;
    // "+N more" pseudo nodes resolve to their host so clicking opens the
    // host's full service list in Checkmk.
    const hostNameForCheckmk = isService || d.nodeType === 'more' ? d.hostId : d.id;
    return {
        id: d.id,
        type: isService ? 'service' : 'host',
        x: 0,
        y: 0,
        host_name: hostNameForCheckmk,
        service_description: svcName,
    } as BoardObject;
}

function objectStateFromFNode(d: FNode): ObjectState {
    const topo = d.topo;
    return {
        object_id: d.id,
        type: d.nodeType,
        state: d.state as ObjectState['state'],
        output: d.output,
        perf_data: '',
        acknowledged: topo?.acknowledged ?? false,
        in_downtime: topo?.in_downtime ?? false,
        stale: false,
        notifications_enabled: topo?.notifications_enabled ?? true,
        active_checks_enabled: topo?.active_checks_enabled ?? true,
        alias: topo?.alias,
        address: topo?.address,
        site_id: topo?.site_id ?? null,
        last_check: topo?.last_check ?? null,
        next_check: topo?.next_check ?? null,
        last_state_change: topo?.last_state_change ?? null,
        state_type: topo?.state_type,
        current_attempt: topo?.current_attempt,
        max_attempts: topo?.max_attempts,
        services_summary: topo?.services_summary ?? null,
    };
}

let simulation: ReturnType<typeof forceSimulation<FNode>> | null = null;
let zoomBeh: ReturnType<typeof zoom<SVGSVGElement, unknown>> | null = null;
let lastFNodes: FNode[] = [];
let _hasFitOnce = false;
// F3 LoD: when zoomed out below this scale we hide service / "+more" nodes and
// their links — they're unreadable at that size and dominate the tick cost.
const LOD_LOW_SCALE = 0.5;
let lodLow = false;

function applyLod(): void {
    if (!svgEl.value) return;
    const display = lodLow ? 'none' : '';
    const sel = select(svgEl.value);
    sel.selectAll<SVGGElement, FNode>('g.node')
        .filter((d) => d.nodeType === 'service' || d.nodeType === 'more')
        .style('display', display);
    sel.selectAll<SVGLineElement, FLink>('g.links line')
        .filter((d) => d.isServiceLink)
        .style('display', display);
}

// Reset auto-fit when switching boards
watch(
    () => props.connectionId,
    () => {
        _hasFitOnce = false;
        lodLow = false;
    },
);

watch(
    () => [
        props.flowView?.root ?? '',
        props.flowView?.child_layers ?? null,
        props.flowView?.parent_layers ?? null,
    ],
    () => {
        nodeCache.clear();
        _hasFitOnce = false;
        fetchTopology();
    },
);

// Stable node map — keeps d3 positions across topology refreshes
const nodeCache = new Map<string, FNode>();

// ---- BFS level (loose — for forceY only) ----
function bfsLevels(topoNodes: TopologyNode[]): Map<string, number> {
    const nameSet = new Set(topoNodes.map((n) => n.name));
    const levels = new Map<string, number>();
    const roots = topoNodes.filter(
        (n) => !n.parents.length || n.parents.every((p) => !nameSet.has(p)),
    );
    const queue: string[] = roots.map((r) => r.name);
    roots.forEach((r) => levels.set(r.name, 0));
    while (queue.length) {
        const name = queue.shift()!;
        const lvl = levels.get(name)!;
        for (const n of topoNodes) {
            if (n.parents.includes(name) && !levels.has(n.name)) {
                levels.set(n.name, lvl + 1);
                queue.push(n.name);
            }
        }
    }
    topoNodes.filter((n) => !levels.has(n.name)).forEach((n) => levels.set(n.name, levels.size));
    return levels;
}

// ---- Zoom controls ----
function fitView() {
    const svg = svgEl.value;
    if (!svg || !zoomBeh || !lastFNodes.length) return;
    const W = svg.clientWidth || 900;
    const H = svg.clientHeight || 600;
    const PAD = 64;
    const xs = lastFNodes.map((n) => n.x ?? n.fx ?? 0);
    const ys = lastFNodes.map((n) => n.y ?? n.fy ?? 0);
    const minX = Math.min(...xs) - NODE_R - PAD;
    const maxX = Math.max(...xs) + NODE_R + PAD;
    const minY = Math.min(...ys) - NODE_R - PAD;
    const maxY = Math.max(...ys) + NODE_R + PAD;
    const scale = Math.min(3, Math.max(0.15, Math.min(W / (maxX - minX), H / (maxY - minY))));
    const tx = W / 2 - scale * ((minX + maxX) / 2);
    const ty = H / 2 - scale * ((minY + maxY) / 2);
    select(svg)
        .transition()
        .duration(500)
        .call(zoomBeh.transform, zoomIdentity.translate(tx, ty).scale(scale));
}

function zoomIn() {
    if (!svgEl.value || !zoomBeh) return;
    select(svgEl.value).transition().duration(200).call(zoomBeh.scaleBy, 1.4);
}

function zoomOut() {
    if (!svgEl.value || !zoomBeh) return;
    select(svgEl.value)
        .transition()
        .duration(200)
        .call(zoomBeh.scaleBy, 1 / 1.4);
}

// ---- D3 rendering ----
watch(
    [nodes, svgEl],
    () => {
        const svg = svgEl.value;
        if (!svg || !nodes.value.length) return;
        render(svg, nodes.value);
    },
    { flush: 'post' },
);

function render(svg: SVGSVGElement, topoNodes: TopologyNode[]) {
    const el = select(svg);
    const W = svg.clientWidth || 900;
    const H = svg.clientHeight || 600;

    // --- Ensure static containers exist (created once) ---
    let gZoom = el.select<SVGGElement>('g.zoom-layer');
    if (gZoom.empty()) {
        gZoom = el.append('g').attr('class', 'zoom-layer');
        gZoom.append('g').attr('class', 'links');
        gZoom.append('g').attr('class', 'nodes');
    }

    // --- Zoom behaviour (attached once) ---
    if (!(el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached) {
        (el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached = true;
        zoomBeh = zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.15, 3])
            .on('zoom', (event) => {
                gZoom.attr('transform', event.transform);
                const newLow = event.transform.k < LOD_LOW_SCALE;
                if (newLow !== lodLow) {
                    lodLow = newLow;
                    applyLod();
                }
            });
        el.call(zoomBeh);
        // Center immediately so nodes don't flash at top-left on first render
        el.call(zoomBeh.transform, zoomIdentity.translate(W / 2, H / 2));
    }

    // --- Build FNode list (reuse cached positions) ---
    const levels = bfsLevels(topoNodes);
    const maxLvl = Math.max(0, ...levels.values());
    // When services are visible, increase vertical spacing to fit service rings.
    // Fan only extends downward so it needs ~half the inter-host gap of orbit.
    const maxSvcN = Math.max(0, ...[...(nodes.value ?? []).map((n) => n.services?.length ?? 0)]);
    const minVSpacing =
        needsServices(props.serviceLayout) && maxSvcN > 0
            ? props.serviceLayout === 'fan'
                ? fanR(maxSvcN) + 50
                : orbitR(maxSvcN) * 2 + 50
            : 0;
    const vSpacing = Math.max(minVSpacing, Math.min(130, (H * 0.8) / Math.max(1, maxLvl + 1)));

    // Host nodes first
    const fNodes: FNode[] = topoNodes.map((n) => {
        const cached = nodeCache.get(n.name);
        const node: FNode = cached
            ? {
                  ...cached,
                  state: n.state,
                  output: n.output,
                  bfsLevel: levels.get(n.name) ?? 0,
                  nodeType: 'host',
                  topo: n,
              }
            : {
                  id: n.name,
                  state: n.state,
                  output: n.output,
                  bfsLevel: levels.get(n.name) ?? 0,
                  nodeType: 'host',
                  topo: n,
              };
        nodeCache.set(n.name, node);
        return node;
    });

    // Service nodes appended after host nodes. When the backend reports a
    // truncation (services_truncated_count > 0) we append one "+M more" pseudo
    // node so users still see that the host has additional services.
    function pushChildNode(seed: Omit<FNode, keyof SimulationNodeDatum>): void {
        const cached = nodeCache.get(seed.id);
        const node: FNode = cached ? { ...cached, ...seed } : { ...seed };
        nodeCache.set(seed.id, node);
        fNodes.push(node);
    }
    if (needsServices(props.serviceLayout)) {
        for (const n of topoNodes) {
            if (!n.services) continue;
            const hostLevel = levels.get(n.name) ?? 0;
            const truncated = n.services_truncated_count ?? 0;
            const N = n.services.length + (truncated > 0 ? 1 : 0);
            for (const svc of n.services) {
                pushChildNode({
                    id: `${n.name}::${svc.name}`,
                    state: svc.state,
                    output: svc.output,
                    bfsLevel: hostLevel,
                    nodeType: 'service',
                    hostId: n.name,
                    svcTotalCount: N,
                });
            }
            if (truncated > 0) {
                pushChildNode({
                    id: `${n.name}::${MORE_NODE_MARKER}`,
                    state: 'PENDING',
                    output: `${truncated} more service${truncated === 1 ? '' : 's'}`,
                    bfsLevel: hostLevel,
                    nodeType: 'more',
                    hostId: n.name,
                    svcTotalCount: N,
                    moreCount: truncated,
                });
            }
        }
    }

    // Remove stale cached nodes
    const activeIds = new Set(fNodes.map((n) => n.id));
    for (const k of nodeCache.keys()) {
        if (!activeIds.has(k)) nodeCache.delete(k);
    }

    const nodeById = new Map(fNodes.map((n) => [n.id, n]));

    const fLinks: FLink[] = [];
    // Host-to-host links
    for (const n of topoNodes) {
        for (const p of n.parents) {
            const src = nodeById.get(p);
            const tgt = nodeById.get(n.name);
            if (src && tgt)
                fLinks.push({
                    source: src,
                    target: tgt,
                    sourceState: src.state,
                    isServiceLink: false,
                });
        }
    }
    // Host-to-service links (and host-to-"+more" link if truncated)
    if (needsServices(props.serviceLayout)) {
        for (const n of topoNodes) {
            if (!n.services) continue;
            const hostNode = nodeById.get(n.name);
            if (!hostNode) continue;
            const moreNode = nodeById.get(`${n.name}::${MORE_NODE_MARKER}`);
            if (moreNode)
                fLinks.push({
                    source: hostNode,
                    target: moreNode,
                    sourceState: hostNode.state,
                    isServiceLink: true,
                });
            for (const svc of n.services) {
                const svcNode = nodeById.get(`${n.name}::${svc.name}`);
                if (svcNode)
                    fLinks.push({
                        source: hostNode,
                        target: svcNode,
                        sourceState: hostNode.state,
                        isServiceLink: true,
                    });
            }
        }
    }

    // Pre-compute service groups per host for fan layout. The "+more" pseudo
    // node participates in the layout so it gets its own slot in the orbit/fan.
    const servicesByHost = new Map<string, FNode[]>();
    for (const n of fNodes) {
        if ((n.nodeType === 'service' || n.nodeType === 'more') && n.hostId) {
            const arr = servicesByHost.get(n.hostId) ?? [];
            arr.push(n);
            servicesByHost.set(n.hostId, arr);
        }
    }

    // Measured row spacings per host (populated after first DOM render)
    const rowSpacings = new Map<string, number>();

    // Service positioning
    function updateFanPositions() {
        for (const [hostId, services] of servicesByHost) {
            const host = nodeById.get(hostId);
            if (!host) continue;
            const hx = host.x ?? 0;
            const hy = host.y ?? 0;
            const N = services.length;

            if (props.serviceLayout === 'fan') {
                // Semicircle below host — radius scales with N so points don't overlap
                const R = fanR(N);
                const spread = N > 1 ? FAN_SPREAD : 0;
                services.forEach((svc, i) => {
                    const angle = Math.PI / 2 + (N > 1 ? -spread / 2 + (i * spread) / (N - 1) : 0);
                    svc.fx = hx + R * Math.cos(angle);
                    svc.fy = hy + R * Math.sin(angle);
                });
            } else if (props.serviceLayout === 'orbit') {
                const R = orbitR(N);
                services.forEach((svc, i) => {
                    const angle = (2 * Math.PI * i) / N - Math.PI / 2;
                    svc.fx = hx + R * Math.cos(angle);
                    svc.fy = hy + R * Math.sin(angle);
                });
            } else {
                // Row: compact grid with automatic wrapping
                const r = svcR(N);
                const cols = Math.min(N, Math.max(4, Math.ceil(Math.sqrt(N * 1.5))));
                const measured = rowSpacings.get(hostId);
                const fallback = services.reduce(
                    (max, svc) => {
                        const label = svc.id.split('::').at(-1) ?? svc.id;
                        return Math.max(max, label.length * 5.5 + 8);
                    },
                    r * 2 + 14,
                );
                const spacingX = measured ?? fallback;
                const spacingY = r * 2 + (showSvcLabel(N) ? 26 : 6);
                const yOffset = NODE_R + r + 22;
                services.forEach((svc, i) => {
                    const col = i % cols;
                    const row = Math.floor(i / cols);
                    svc.fx = hx + (col - (cols - 1) / 2) * spacingX;
                    svc.fy = hy + yOffset + row * spacingY;
                });
            }
        }
    }
    updateFanPositions();
    lastFNodes = fNodes;

    // --- Update simulation ---
    if (simulation) simulation.stop();

    const hostLinks = fLinks.filter((l) => !l.isServiceLink);

    simulation = forceSimulation<FNode>(fNodes)
        .force(
            'link',
            forceLink<FNode, FLink>(hostLinks)
                .id((d) => d.id)
                .distance((d) => {
                    // Space hosts far enough apart that their service rings don't overlap
                    const srcN = servicesByHost.get((d.source as FNode).id)?.length ?? 0;
                    const tgtN = servicesByHost.get((d.target as FNode).id)?.length ?? 0;
                    if (srcN === 0 && tgtN === 0) return 160;
                    return Math.max(200, layoutR(srcN) + layoutR(tgtN) + 60);
                })
                .strength(0.4),
        )
        .force(
            'charge',
            forceManyBody<FNode>().strength((d) => {
                if (d.nodeType === 'service') return 0;
                const N = servicesByHost.get(d.id)?.length ?? 0;
                // Modest extra repulsion so service rings don't crowd; collision handles the hard min
                return N > 0 ? -Math.max(700, layoutR(N) * 9) : -600;
            }),
        )
        .force(
            'center',
            forceX<FNode>(0).strength((d) => (d.nodeType === 'host' ? 0.05 : 0)),
        )
        .force(
            'collide',
            forceCollide<FNode>((d) => {
                if (d.nodeType === 'service') return 0;
                const svcs = servicesByHost.get(d.id) ?? [];
                const N = svcs.length;
                if (N === 0 || !needsServices(props.serviceLayout)) {
                    // Donut sits directly on the host — reserve the donut width
                    // for donut layout and for top-K-omitted hosts in fan/orbit/row.
                    const wantsDonut =
                        props.serviceLayout === 'donut' || (d.topo?.services_omitted ?? false);
                    return wantsDonut ? NODE_R + 14 : NODE_R + 10;
                }
                if (props.serviceLayout === 'fan' || props.serviceLayout === 'orbit')
                    return layoutR(N) + svcR(N) + 20;
                // Row grid
                const cols = Math.min(N, Math.max(4, Math.ceil(Math.sqrt(N * 1.5))));
                const spacingX = rowSpacings.get(d.id) ?? 60;
                return (cols / 2) * spacingX + svcR(N) + 10;
            }).iterations(3),
        )
        .force(
            'y',
            forceY<FNode>((d) => (d.bfsLevel - maxLvl / 2) * vSpacing).strength((d) =>
                d.nodeType === 'service' ? 0 : 0.4,
            ),
        )
        .alphaDecay(0.03)
        .stop();

    // --- Drag behaviour ---
    const dragBehavior = drag<SVGGElement, FNode>()
        .on('start', (event, d) => {
            if (!event.active) simulation!.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        })
        .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
        })
        .on('end', (event, d) => {
            if (!event.active) simulation!.alphaTarget(0);
            d.fx = d.x;
            d.fy = d.y;
        });

    // --- Links ---
    const gLinks = gZoom.select<SVGGElement>('g.links');
    const linkSel = gLinks
        .selectAll<SVGLineElement, FLink>('line')
        .data(fLinks, (d) => `${(d.source as FNode).id}→${(d.target as FNode).id}`);
    linkSel.exit().remove();
    const linkEnter = linkSel.enter().append('line');
    const linkMerge = linkEnter
        .merge(linkSel)
        .attr('stroke', (d) => stateColor((d.source as FNode).state))
        .attr('stroke-opacity', (d) => (d.isServiceLink ? 0.3 : 0.45))
        .attr('stroke-width', (d) => (d.isServiceLink ? 1 : 1.5))
        .attr('stroke-dasharray', (d) => (d.isServiceLink ? '3,3' : null));

    // --- Nodes ---
    const gNodes = gZoom.select<SVGGElement>('g.nodes');
    const nodeSel = gNodes.selectAll<SVGGElement, FNode>('g.node').data(fNodes, (d) => d.id);
    nodeSel.exit().remove();

    const nodeEnter = nodeSel
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('cursor', (d) => {
            if (d.nodeType === 'host' && !props.readonly) return 'grab';
            return props.clickAction === 'none' ? 'default' : 'pointer';
        })
        .on('click', (_event, d) => {
            if (props.clickAction === 'none') return;
            const url = buildCheckmkUrl(boardObjectFromFNode(d), props.checkmkUrl ?? null);
            if (url) openUrl(url, '_blank');
        })
        .on('mouseenter', (event: MouseEvent, d) => {
            const nodeRect = (event.currentTarget as SVGGElement).getBoundingClientRect();
            hoverMenu.object = boardObjectFromFNode(d);
            hoverMenu.state = objectStateFromFNode(d);
            hoverMenu.x = nodeRect.right + 8;
            hoverMenu.y = nodeRect.top;
            hoverMenu.visible = true;
        })
        .on('mouseleave', () => {
            hoverMenu.visible = false;
            hoverMenu.object = null;
        });

    // Drag only on host nodes when not in readonly/kiosk mode
    if (!props.readonly) {
        nodeEnter.filter((d) => d.nodeType === 'host').call(dragBehavior as never);
    }

    // Host nodes
    const hostEnter = nodeEnter.filter((d) => d.nodeType === 'host');
    hostEnter
        .append('circle')
        .attr('r', NODE_R)
        .attr('stroke', 'rgba(0,0,0,0.4)')
        .attr('stroke-width', 1.5);
    // Empty donut container — actual segments are bound in the update pass below.
    hostEnter.append('g').attr('class', 'donut').attr('pointer-events', 'none');
    hostEnter
        .append('text')
        .attr('class', 'type-char')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('fill', 'rgba(255,255,255,0.9)')
        .attr('font-size', 11)
        .attr('font-weight', '700')
        .attr('pointer-events', 'none')
        .text('H');
    hostEnter
        .append('text')
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'hanging')
        .attr('font-size', 11)
        .attr('font-weight', '500')
        .attr('pointer-events', 'none')
        .style('fill', 'var(--text)')
        .attr('y', NODE_R + 5);

    // Service nodes
    const svcEnter = nodeEnter.filter((d) => d.nodeType === 'service');
    svcEnter
        .append('circle')
        .attr('r', (d) => svcR(d.svcTotalCount ?? 1))
        .attr('stroke', 'rgba(0,0,0,0.4)')
        .attr('stroke-width', 1);
    svcEnter
        .append('text')
        .attr('class', 'type-char')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('fill', 'rgba(255,255,255,0.9)')
        .attr('font-size', (d) => (svcR(d.svcTotalCount ?? 1) <= 7 ? 6 : 8))
        .attr('font-weight', '700')
        .attr('pointer-events', 'none')
        .text('S');
    svcEnter
        .append('text')
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'hanging')
        .attr('font-size', 9)
        .attr('font-weight', '400')
        .attr('pointer-events', 'none')
        .style('fill', 'var(--text)')
        .attr('y', (d) => svcR(d.svcTotalCount ?? 1) + 4)
        .style('display', (d) => (showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none'));

    // "+N more" pseudo nodes: same shape as services but with a neutral fill
    // and a `+N` glyph. They're not real services — clicking opens the host's
    // service list in Checkmk (handled in the shared click handler below).
    const moreEnter = nodeEnter.filter((d) => d.nodeType === 'more');
    moreEnter
        .append('circle')
        .attr('r', (d) => svcR(d.svcTotalCount ?? 1))
        .attr('stroke', 'rgba(0,0,0,0.4)')
        .attr('stroke-width', 1);
    moreEnter
        .append('text')
        .attr('class', 'type-char')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('fill', 'rgba(255,255,255,0.95)')
        .attr('font-size', (d) => (svcR(d.svcTotalCount ?? 1) <= 7 ? 7 : 9))
        .attr('font-weight', '700')
        .attr('pointer-events', 'none')
        .text((d) => `+${d.moreCount ?? 0}`);
    moreEnter
        .append('text')
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'hanging')
        .attr('font-size', 9)
        .attr('font-weight', '400')
        .attr('pointer-events', 'none')
        .style('fill', 'var(--text)')
        .attr('y', (d) => svcR(d.svcTotalCount ?? 1) + 4)
        .text((d) => `+${d.moreCount ?? 0} more`)
        .style('display', (d) => (showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none'));

    const nodeMerge = nodeEnter.merge(nodeSel);
    nodeMerge.select('circle').attr('fill', (d) => stateColor(d.state));

    // Donut update — bind aggregated services_summary as proportional arcs on
    // each host. Always rendered in donut layout; in fan/orbit/row only for
    // hosts whose service detail wasn't fetched (top-K cutoff in the backend),
    // so the user still sees an at-a-glance state aggregate. The exit() removes
    // leftover paths when a host transitions out of either condition.
    nodeMerge
        .filter((d) => d.nodeType === 'host')
        .each(function (d) {
            const showDonut =
                props.serviceLayout === 'donut' || (d.topo?.services_omitted ?? false);
            const segments = showDonut && d.topo ? donutSegments(d.topo) : [];
            const arcs = donutPie(segments);
            const donutG = select(this).select<SVGGElement>('g.donut');
            const paths = donutG
                .selectAll<SVGPathElement, (typeof arcs)[number]>('path')
                .data(arcs, (a) => a.data.state);
            paths.exit().remove();
            paths
                .enter()
                .append('path')
                .merge(paths)
                .attr('d', (a) => donutArc(a) ?? '')
                .attr('fill', (a) => stateColor(a.data.state))
                .attr('stroke', 'rgba(0,0,0,0.35)')
                .attr('stroke-width', 0.5);
        });
    nodeMerge.select('text.node-label').text((d) => {
        if (d.nodeType === 'more') return `+${d.moreCount ?? 0} more`;
        if (d.nodeType === 'service') {
            const parts = d.id.split('::');
            return parts[parts.length - 1];
        }
        return d.id;
    });
    // Refresh service / more-label visibility — may change when switching layout or on re-render
    nodeMerge
        .filter((d) => d.nodeType === 'service' || d.nodeType === 'more')
        .select('text.node-label')
        .style('display', (d) => (showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none'));

    // --- Tick handler ---
    // The first paint can race the d3-force `initializeNodes` step on layout
    // switches that null out cached host positions, so coerce non-finite
    // coordinates to 0 to avoid SVG attribute errors (the next tick fixes them).
    const _coord = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
    function ticked() {
        updateFanPositions();
        linkMerge
            .attr('x1', (d) => _coord((d.source as FNode).x))
            .attr('y1', (d) => _coord((d.source as FNode).y))
            .attr('x2', (d) => _coord((d.target as FNode).x))
            .attr('y2', (d) => _coord((d.target as FNode).y))
            .attr('stroke', (d) => stateColor((d.source as FNode).state));

        nodeMerge
            .attr('transform', (d) => `translate(${_coord(d.x)},${_coord(d.y)})`)
            .select('circle')
            .attr('fill', (d) => stateColor(d.state));
    }

    // Measure actual row-label widths from the DOM before the simulation starts;
    // updateFanPositions reads `rowSpacings` to lay out the row grid.
    if (props.serviceLayout === 'row') {
        for (const [hostId, services] of servicesByHost) {
            const N = services.length;
            if (!showSvcLabel(N)) {
                rowSpacings.set(hostId, svcR(N) * 2 + 6);
                continue;
            }
            let maxW = 0;
            for (const svc of services) {
                const g = gNodes
                    .selectAll<SVGGElement, FNode>('g.node')
                    .filter((d) => d.id === svc.id)
                    .node();
                const textEl = g?.querySelector<SVGTextElement>('text.node-label');
                if (textEl) maxW = Math.max(maxW, textEl.getComputedTextLength());
            }
            if (maxW > 0) rowSpacings.set(hostId, maxW + 10);
        }
    }

    // Paint once with cached/initial positions so users see something immediately.
    updateFanPositions();
    ticked();
    // Reapply LoD so newly entered service / "+more" nodes pick up the
    // current zoom-driven display state.
    applyLod();

    // F1: don't synchronously tick(250) — that blocks the main thread for
    // hundreds of ms at scale. Let the simulation converge asynchronously and
    // defer the initial fit until it has settled enough.
    const isInitial = !_hasFitOnce;
    simulation
        .on('tick', ticked)
        .alpha(isInitial ? 1 : 0.2)
        .restart();
    if (isInitial) {
        _hasFitOnce = true;
        let ticksUntilFit = needsServices(props.serviceLayout) ? 60 : 40;
        simulation.on('tick.fit', () => {
            if (--ticksUntilFit <= 0) {
                simulation?.on('tick.fit', null);
                fitView();
            }
        });
    }
}
</script>
