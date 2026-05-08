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
                @click="fitView()"
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

        <div v-if="!loading && !error && !detailObject" class="flow-search">
            <svg
                style="width: 12px; height: 12px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
                class="text-zinc-400 shrink-0"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 105.62 5.62a7.5 7.5 0 0011.03 11.03z"
                />
            </svg>
            <input
                v-model="filterText"
                :placeholder="t('board.flow.searchPlaceholder')"
                type="search"
                class="flow-search__input"
                aria-label="Search hosts and services"
            />
            <button
                v-if="filterText"
                type="button"
                class="flow-search__clear"
                @click="filterText = ''"
            >
                ×
            </button>
            <button
                type="button"
                class="flow-search__toggle"
                :class="{ 'flow-search__toggle--active': stateFilter === 'problems' }"
                :title="t('board.flow.problemsOnlyToggle')"
                @click="stateFilter = stateFilter === 'problems' ? 'all' : 'problems'"
            >
                <svg
                    style="width: 12px; height: 12px"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                    />
                </svg>
            </button>
        </div>

        <div
            v-if="topKBreakdown.omitted > 0 && needsServiceDetail"
            class="flow-hint flow-hint--topk"
        >
            {{ t('board.flow.topKHint', topKBreakdown) }}
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

        <DetailDrawer
            :object="detailObject"
            :state="detailState"
            :checkmk-url="props.checkmkUrl ?? null"
            :connection-id="props.connectionId ?? null"
            :selectable-hosts="flowSelectableHosts"
            portal-target="#orbvis-board-shell"
            @close="closeDetail"
            @acknowledge="onDetailAck"
            @remove-ack="onDetailRemoveAck"
            @schedule-downtime="onDetailDowntime"
            @remove-downtime="onDetailRemoveDowntime"
            @force-check="onDetailForceCheck"
            @add-comment="onDetailAddComment"
            @enable-notifications="onDetailToggleNotifications(true)"
            @disable-notifications="onDetailToggleNotifications(false)"
            @select-host="onSelectFlowHost"
        />

        <div v-if="selectedIds.size > 0" class="bulk-actions">
            <span class="bulk-actions__count">
                {{ t('board.flow.bulkSelected', { count: selectedIds.size }) }}
            </span>
            <button
                type="button"
                class="bulk-actions__btn"
                @click="bulkAction(objectActions.handlers.acknowledge)"
            >
                {{ t('contextMenu.acknowledge') }}
            </button>
            <button
                type="button"
                class="bulk-actions__btn"
                @click="bulkAction(objectActions.handlers.scheduleDowntime)"
            >
                {{ t('contextMenu.scheduleDowntime') }}
            </button>
            <button
                type="button"
                class="bulk-actions__btn"
                @click="bulkAction(objectActions.handlers.forceCheck)"
            >
                {{ t('contextMenu.forceCheck') }}
            </button>
            <button
                type="button"
                class="bulk-actions__btn bulk-actions__btn--clear"
                @click="clearSelection"
            >
                ×
            </button>
        </div>

        <!-- Context menu (right-click) -->
        <ContextMenu
            v-if="contextMenu.visible && contextMenu.object"
            :object="contextMenu.object"
            :state="contextMenu.state"
            :x="contextMenu.x"
            :y="contextMenu.y"
            :checkmk-url="props.checkmkUrl ?? null"
            @close="closeContextMenu"
            @acknowledge="onContextMenuAck"
            @remove-ack="onContextMenuRemoveAck"
            @schedule-downtime="onContextMenuDowntime"
            @remove-downtime="onContextMenuRemoveDowntime"
            @force-check="onContextMenuForceCheck"
            @add-comment="onContextMenuAddComment"
            @enable-notifications="onContextMenuToggleNotifications(true)"
            @disable-notifications="onContextMenuToggleNotifications(false)"
        />
    </div>

    <AckModal
        v-if="ackModalObject && props.checkmkUrl"
        :object="ackModalObject"
        :checkmk-url="props.checkmkUrl"
        @close="
            ackModalObject = null;
            statesStore.refreshAfterCommand();
        "
    />

    <CommentModal
        v-if="commentModalObject && props.checkmkUrl"
        :object="commentModalObject"
        :checkmk-url="props.checkmkUrl"
        @close="commentModalObject = null"
    />

    <DowntimeModal
        v-if="downtimeModalObject && props.checkmkUrl"
        :object="downtimeModalObject"
        :checkmk-url="props.checkmkUrl"
        @close="
            downtimeModalObject = null;
            statesStore.refreshAfterCommand();
        "
    />

    <RemoveDowntimeModal
        v-if="removeDowntimeModal.visible && props.checkmkUrl"
        :downtimes="removeDowntimeModal.downtimes"
        :checkmk-url="props.checkmkUrl"
        :object-name="removeDowntimeModal.objectName"
        @close="
            removeDowntimeModal.visible = false;
            statesStore.refreshAfterCommand();
        "
    />
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
    type ZoomTransform,
} from 'd3';
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi } from '@/api/client';
import AckModal from '@/components/board/AckModal.vue';
import CommentModal from '@/components/board/CommentModal.vue';
import ContextMenu from '@/components/board/ContextMenu.vue';
import DetailDrawer from '@/components/board/DetailDrawer.vue';
import DowntimeModal from '@/components/board/DowntimeModal.vue';
import HoverMenu from '@/components/board/HoverMenu.vue';
import RemoveDowntimeModal from '@/components/board/RemoveDowntimeModal.vue';
import { useD3Cleanup } from '@/composables/useD3Cleanup';
import { useObjectActions } from '@/composables/useObjectActions';
import { useAuthStore } from '@/stores/auth';
import { useStatesStore } from '@/stores/states';
import type {
    BoardObject,
    ClickAction,
    FlowView,
    ObjectState,
    ServiceLayout,
    ServiceNode,
    TopologyNode,
} from '@/types/api';
import { buildCheckmkUrl, openUrl } from '@/utils/boardNavigation';
import { stateColor } from '@/utils/stateColors';

const props = defineProps<{
    connectionId: string;
    serviceLayout: ServiceLayout;
    readonly?: boolean;
    clickAction?: ClickAction;
    checkmkUrl?: string | null;
    flowView?: FlowView | null;
}>();
const emit = defineEmits<{
    (e: 'update:serviceLayout', value: ServiceLayout): void;
    (
        e: 'update:problems',
        value: { critical: number; warning: number; hostsWithProblems: number; total: number },
    ): void;
    (e: 'drawer-object', value: BoardObject | null): void;
    (e: 'positions-changed', value: Record<string, { x: number; y: number }>): void;
}>();
const { t } = useI18n();
const auth = useAuthStore();
const statesStore = useStatesStore();

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
// Width grows inversely with zoom so the ring stays ≥ DONUT_MIN_SCREEN_PX on
// fit-to-view of dense boards — otherwise an 8 model-px ring collapses to <2 px
// screen at scale ~0.2 and the entire status aggregate becomes invisible.
const DONUT_INNER = NODE_R + 3;
const DONUT_BASE_WIDTH = 8;
const DONUT_MIN_SCREEN_PX = 4;
const DONUT_MAX_WIDTH = 24;
function donutOuterRadius(zoomK: number): number {
    const widthForMinScreen = DONUT_MIN_SCREEN_PX / Math.max(zoomK, 0.0001);
    const width = Math.min(DONUT_MAX_WIDTH, Math.max(DONUT_BASE_WIDTH, widthForMinScreen));
    return DONUT_INNER + width;
}
type DonutSegment = { state: 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING'; value: number };
type DonutArc = { startAngle: number; endAngle: number };
function buildDonutArc(zoomK: number) {
    return d3arc<DonutArc>().innerRadius(DONUT_INNER).outerRadius(donutOuterRadius(zoomK));
}
const donutPie = d3pie<DonutSegment>()
    .sort(null)
    .value((d) => d.value);

// Border halo on the host glyph; the fill stays the host's own state so the
// host-DOWN vs. host-UP-with-CRIT-services distinction isn't erased.
const HALO_DEFAULT_STROKE = 'rgba(0,0,0,0.4)';
const HEALTHY_HOST_STATES = new Set(['UP', 'OK', 'PENDING']);

function worstServiceState(d: FNode): string | null {
    const s = d.topo?.services_summary;
    if (!s) return null;
    if (s.critical > 0) return 'CRITICAL';
    if (s.warning > 0) return 'WARNING';
    if (s.unknown > 0) return 'UNKNOWN';
    return null;
}

function hostHalo(d: FNode): { stroke: string; width: number } {
    const isTopK = topKWorstIds.value.has(d.id);
    if (!HEALTHY_HOST_STATES.has(d.state)) {
        return isTopK
            ? { stroke: stateColor(d.state), width: 4 }
            : { stroke: HALO_DEFAULT_STROKE, width: 1.5 };
    }
    const worst = worstServiceState(d);
    if (!worst) return { stroke: HALO_DEFAULT_STROKE, width: 1.5 };
    return { stroke: stateColor(worst), width: isTopK ? 4 : 2.5 };
}

function problemScoreFromTopo(n: TopologyNode): number {
    const hostPenalty = HEALTHY_HOST_STATES.has(n.state) ? 0 : 100;
    const s = n.services_summary;
    if (!s) return hostPenalty;
    return hostPenalty + s.critical * 4 + s.warning * 2 + s.unknown * 2;
}

// Severity rank: 2 = critical/down, 1 = warn/unknown, 0 = ok.
// Used for the initial spiral pre-layout (problems toward the center) and
// for severity-stratified forceX/forceY targets so high-severity hosts stay
// near origin instead of getting flung to the rim by charge alone.
function severityRank(n: TopologyNode | undefined): 0 | 1 | 2 {
    if (!n) return 0;
    if (!HEALTHY_HOST_STATES.has(n.state)) return 2;
    const s = n.services_summary;
    if (!s) return 0;
    if (s.critical > 0) return 2;
    if (s.warning > 0 || s.unknown > 0) return 1;
    return 0;
}

// Phyllotaxis (sunflower) layout: even-density spiral with no holes. Sorting
// by severity rank (desc) means hosts with the worst state get the inner
// slots, healthy hosts the outer. The combined effect is a compact disk
// whose center is dominated by problems and whose rim is mostly green —
// readable at a glance even on 500-host boards.
const PHYLLOTAXIS_ANGLE = Math.PI * (3 - Math.sqrt(5));
const SPIRAL_SPACING = 55;
function preLayoutHosts(hosts: FNode[]): void {
    if (!hosts.length) return;
    const ranked = [...hosts].sort((a, b) => {
        const sa = severityRank(a.topo);
        const sb = severityRank(b.topo);
        if (sa !== sb) return sb - sa;
        return a.id.localeCompare(b.id);
    });
    ranked.forEach((d, i) => {
        const angle = i * PHYLLOTAXIS_ANGLE;
        const r = SPIRAL_SPACING * Math.sqrt(i + 1);
        d.x = r * Math.cos(angle);
        d.y = r * Math.sin(angle);
    });
}

const TOP_K_LIMIT = 5;
const TOP_K_THRESHOLD = 50;
const topKWorstIds = computed<Set<string>>(() => {
    if (nodes.value.length < TOP_K_THRESHOLD) return new Set();
    const scored = nodes.value
        .map((n) => ({ id: n.name, score: problemScoreFromTopo(n) }))
        .filter((s) => s.score > 0)
        .sort((a, b) => b.score - a.score);
    return new Set(scored.slice(0, TOP_K_LIMIT).map((s) => s.id));
});

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

const contextMenu = reactive<{
    visible: boolean;
    object: BoardObject | null;
    state: ObjectState | undefined;
    x: number;
    y: number;
}>({ visible: false, object: null, state: undefined, x: 0, y: 0 });

function closeContextMenu(): void {
    contextMenu.visible = false;
    contextMenu.object = null;
}

// Multi-select: shift-clicking nodes builds a set; bulk-action toolbar applies
// host/service ops sequentially over the set.
const selectedIds = ref<Set<string>>(new Set());
const selectedFNodes = new Map<string, FNode>();

function toggleSelection(d: FNode): void {
    if (selectedIds.value.has(d.id)) {
        selectedIds.value.delete(d.id);
        selectedFNodes.delete(d.id);
    } else {
        selectedIds.value.add(d.id);
        selectedFNodes.set(d.id, d);
    }
    selectedIds.value = new Set(selectedIds.value);
    applySelectionStyles();
}

function clearSelection(): void {
    selectedIds.value = new Set();
    selectedFNodes.clear();
    applySelectionStyles();
}

// SELECTION_STROKE matches --color-yellow-50 from cmk/colors.css. Inlined as a
// hex literal because d3 attr() must operate on SVG attribute strings — CSS
// custom properties aren't available there without a getComputedStyle hop.
const SELECTION_STROKE = 'rgb(255, 215, 3)';

function attachLasso(svg: SVGSVGElement): void {
    let startX = 0;
    let startY = 0;
    let lassoEl: SVGRectElement | null = null;
    let active = false;

    const onPointerDown = (event: PointerEvent) => {
        if (!event.shiftKey || event.button !== 0) return;
        const target = event.target as Element;
        if (target.closest('g.node')) return;
        active = true;
        const rect = svg.getBoundingClientRect();
        startX = event.clientX - rect.left;
        startY = event.clientY - rect.top;
        lassoEl = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        lassoEl.setAttribute('fill', 'rgba(255,215,3,0.08)');
        lassoEl.setAttribute('stroke', 'rgb(255,215,3)');
        lassoEl.setAttribute('stroke-dasharray', '4 4');
        lassoEl.setAttribute('pointer-events', 'none');
        svg.appendChild(lassoEl);
        svg.setPointerCapture(event.pointerId);
        event.preventDefault();
    };

    const onPointerMove = (event: PointerEvent) => {
        if (!active || !lassoEl) return;
        const rect = svg.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        const minX = Math.min(startX, x);
        const minY = Math.min(startY, y);
        const w = Math.abs(x - startX);
        const h = Math.abs(y - startY);
        lassoEl.setAttribute('x', String(minX));
        lassoEl.setAttribute('y', String(minY));
        lassoEl.setAttribute('width', String(w));
        lassoEl.setAttribute('height', String(h));
    };

    const onPointerUp = (event: PointerEvent) => {
        if (!active) return;
        active = false;
        svg.releasePointerCapture(event.pointerId);
        const rect = svg.getBoundingClientRect();
        const endX = event.clientX - rect.left;
        const endY = event.clientY - rect.top;
        const minX = Math.min(startX, endX);
        const minY = Math.min(startY, endY);
        const maxX = Math.max(startX, endX);
        const maxY = Math.max(startY, endY);
        if (lassoEl) {
            lassoEl.remove();
            lassoEl = null;
        }
        // Trivial 4-px box = treat as missed-click, do nothing
        if (maxX - minX < 4 && maxY - minY < 4) return;
        select(svg)
            .selectAll<SVGGElement, FNode>('g.node')
            .each(function (d) {
                const r = (this as SVGGElement).getBoundingClientRect();
                const cx = r.x + r.width / 2 - rect.left;
                const cy = r.y + r.height / 2 - rect.top;
                if (cx >= minX && cx <= maxX && cy >= minY && cy <= maxY) {
                    selectedIds.value.add(d.id);
                    selectedFNodes.set(d.id, d);
                }
            });
        selectedIds.value = new Set(selectedIds.value);
        applySelectionStyles();
    };

    svg.addEventListener('pointerdown', onPointerDown);
    svg.addEventListener('pointermove', onPointerMove);
    svg.addEventListener('pointerup', onPointerUp);
    svg.addEventListener('pointercancel', onPointerUp);
}

function applySelectionStyles(): void {
    if (!svgEl.value) return;
    select(svgEl.value)
        .selectAll<SVGGElement, FNode>('g.node')
        .each(function (d) {
            const isSel = selectedIds.value.has(d.id);
            const circle = (this as SVGGElement).querySelector('circle');
            if (!circle) return;
            if (isSel) {
                circle.setAttribute('data-selected', '1');
                circle.setAttribute('stroke', SELECTION_STROKE);
                circle.setAttribute('stroke-width', '3');
            } else if (circle.getAttribute('data-selected') === '1') {
                circle.removeAttribute('data-selected');
                if (d.nodeType === 'host') {
                    const halo = hostHalo(d);
                    circle.setAttribute('stroke', halo.stroke);
                    circle.setAttribute('stroke-width', String(halo.width));
                } else {
                    circle.setAttribute('stroke', 'rgba(0,0,0,0.4)');
                    circle.setAttribute('stroke-width', '1');
                }
            }
        });
}

const selectedObjects = computed(() =>
    [...selectedFNodes.values()].map((d) => boardObjectFromFNode(d)),
);

async function bulkAction(
    handler: (obj: BoardObject | null) => Promise<void> | void,
): Promise<void> {
    const objs = selectedObjects.value.slice();
    for (const obj of objs) {
        await Promise.resolve(handler(obj));
    }
}

const detailObject = ref<BoardObject | null>(null);
const detailFNode = ref<FNode | null>(null);
// Recompute the drawer body whenever topology changes — otherwise a site
// drawer keeps showing the aggregate from the click moment, going stale on
// active boards.
const detailState = computed<ObjectState | undefined>(() => {
    if (!detailFNode.value) return undefined;
    // Touch nodes.value so the computed re-runs on every topology push.
    void nodes.value;
    return objectStateFromFNode(detailFNode.value);
});

// The initial render schedules a refining fitView once the force-simulation
// settles. If the operator clicks a node before that fires, we'd animate the
// layout into a new transform mid-interaction — registered here, called from
// any interaction that should "claim" the current view.
let _cancelPendingFit: (() => void) | null = null;
function cancelPendingFit(): void {
    if (_cancelPendingFit) {
        _cancelPendingFit();
        _cancelPendingFit = null;
    }
}

function openDetail(obj: BoardObject, fNode: FNode): void {
    cancelPendingFit();
    detailObject.value = obj;
    detailFNode.value = fNode;
    closeContextMenu();
}

function closeDetail(): void {
    detailObject.value = null;
    detailFNode.value = null;
}

function onDetailAck(): void {
    objectActions.handlers.acknowledge(detailObject.value);
}
function onDetailRemoveAck(): void {
    objectActions.handlers.removeAck(detailObject.value);
}
function onDetailDowntime(): void {
    objectActions.handlers.scheduleDowntime(detailObject.value);
}
function onDetailRemoveDowntime(): void {
    objectActions.handlers.removeDowntime(detailObject.value);
}
function onDetailForceCheck(): void {
    objectActions.handlers.forceCheck(detailObject.value);
}
function onDetailAddComment(): void {
    objectActions.handlers.addComment(detailObject.value);
}
function onDetailToggleNotifications(enable: boolean): void {
    objectActions.handlers.toggleNotifications(detailObject.value, enable);
}

function onDocumentClick(): void {
    if (contextMenu.visible) closeContextMenu();
}

// Hostnames the Flow Board currently renders — Drawer-Topology entries that
// match these become click-to-jump buttons. Recomputes on every topology push.
const flowSelectableHosts = computed(() => nodes.value.map((n) => n.name));

function onSelectFlowHost(hostName: string): void {
    const node = nodes.value.find((n) => n.name === hostName);
    if (!node) return;
    // Synthesize a BoardObject the Drawer can render — Flow Board nodes don't
    // come from boardConfig.objects, they live in the live topology snapshot.
    detailObject.value = {
        id: `flow-host-${hostName}`,
        type: 'host',
        x: 0,
        y: 0,
        host_name: hostName,
    } as BoardObject;
}

const objectActions = useObjectActions(() => props.checkmkUrl ?? null, closeContextMenu);
const { ackModalObject, downtimeModalObject, commentModalObject, removeDowntimeModal } =
    objectActions;
const onContextMenuAck = () => objectActions.handlers.acknowledge(contextMenu.object);
const onContextMenuRemoveAck = () => objectActions.handlers.removeAck(contextMenu.object);
const onContextMenuDowntime = () => objectActions.handlers.scheduleDowntime(contextMenu.object);
const onContextMenuRemoveDowntime = () => objectActions.handlers.removeDowntime(contextMenu.object);
const onContextMenuAddComment = () => objectActions.handlers.addComment(contextMenu.object);
const onContextMenuForceCheck = () => objectActions.handlers.forceCheck(contextMenu.object);
const onContextMenuToggleNotifications = (enable: boolean) =>
    objectActions.handlers.toggleNotifications(contextMenu.object, enable);

let timer: ReturnType<typeof setInterval> | null = null;

// Layouts that need the full per-host service list. Donut renders only
// services_summary aggregates and therefore skips the bulk query entirely —
// that's the main scaling win for large installations.
function needsServices(layout: typeof props.serviceLayout): boolean {
    return layout === 'fan' || layout === 'orbit' || layout === 'row';
}

// Off-layout hides per-service health; aggregate problem counts to surface
// them in a click-to-fix CTA so a green-dot board doesn't mask CRIT/WARN.
// Total includes UNKNOWN (so unknown-only sites still trigger the banner)
// but the locale string only enumerates the more actionable CRIT/WARN.
const aggregatedProblems = computed(() => {
    let critical = 0;
    let warning = 0;
    let unknown = 0;
    let hostsWithProblems = 0;
    for (const n of nodes.value) {
        const s = n.services_summary;
        if (!s) continue;
        if (s.critical || s.warning || s.unknown) hostsWithProblems++;
        critical += s.critical;
        warning += s.warning;
        unknown += s.unknown;
    }
    return {
        critical,
        warning,
        hostsWithProblems,
        total: critical + warning + unknown,
    };
});

watch(aggregatedProblems, (v) => emit('update:problems', v), { immediate: true });

// Lifted to BoardView so the parent can hide overlapping bottom-right controls
// and render a triage breadcrumb. Emits the actual object so the parent can
// label the breadcrumb without keeping a parallel state copy.
watch(detailObject, (v) => emit('drawer-object', v));

// Coalesce burst drags into a single save: dragging multiple hosts in
// succession or multi-select drags would otherwise hammer boards.update.
let _emitPinnedTimer: ReturnType<typeof setTimeout> | null = null;
function emitPinnedPositions(): void {
    if (_emitPinnedTimer) clearTimeout(_emitPinnedTimer);
    _emitPinnedTimer = setTimeout(() => {
        const positions: Record<string, { x: number; y: number }> = {};
        for (const node of nodeCache.values()) {
            if (
                node.nodeType === 'host' &&
                typeof node.fx === 'number' &&
                typeof node.fy === 'number' &&
                Number.isFinite(node.fx) &&
                Number.isFinite(node.fy)
            ) {
                positions[node.id] = { x: node.fx, y: node.fy };
            }
        }
        emit('positions-changed', positions);
    }, 400);
}
onUnmounted(() => {
    if (_emitPinnedTimer) clearTimeout(_emitPinnedTimer);
});

defineExpose({ closeDetail });

// Top-K cutoff visibility: when fan/orbit/row layouts are active and the
// backend omitted full service detail for some hosts, surface the ratio so
// operators understand why many hosts only show donut rings.
const topKBreakdown = computed(() => {
    const total = nodes.value.length;
    let omitted = 0;
    for (const n of nodes.value) if (n.services_omitted) omitted++;
    return { total, shown: total - omitted, omitted };
});

const needsServiceDetail = computed(() => needsServices(props.serviceLayout));

// Free-text filter: dim (don't hide) nodes that don't match so the spatial
// context is preserved. Hiding would re-trigger force-collide and rearrange
// the whole board on every keystroke. State filter dims healthy hosts/services
// so the operator sees only what needs attention.
type StateFilter = 'all' | 'problems';
const filterText = ref('');
const stateFilter = ref<StateFilter>('all');
const filterNeedle = computed(() => filterText.value.trim().toLowerCase());

function nodeHasProblem(d: FNode): boolean {
    if (d.nodeType === 'host') {
        if (!HEALTHY_HOST_STATES.has(d.state)) return true;
        return worstServiceState(d) !== null;
    }
    return d.state !== 'OK' && d.state !== 'PENDING';
}

function nodeMatchesFilter(d: FNode): boolean {
    if (stateFilter.value === 'problems' && !nodeHasProblem(d)) return false;
    const needle = filterNeedle.value;
    if (!needle) return true;
    if (d.id.toLowerCase().includes(needle)) return true;
    if (d.nodeType === 'service' && d.hostId?.toLowerCase().includes(needle)) return true;
    if (d.nodeType === 'host' && d.topo?.alias?.toLowerCase().includes(needle)) return true;
    return false;
}

const filterIsActive = computed(() => stateFilter.value !== 'all' || filterNeedle.value.length > 0);

watch([filterText, stateFilter], () => {
    if (svgEl.value) applyFilterOpacity();
});

let filterOpacityActive = false;

function applyFilterOpacity(): void {
    if (!svgEl.value) return;
    const sel = select(svgEl.value);
    if (!filterIsActive.value) {
        if (!filterOpacityActive) return;
        filterOpacityActive = false;
        sel.selectAll('g.node, g.links line').attr('opacity', 1);
        return;
    }
    filterOpacityActive = true;
    sel.selectAll<SVGGElement, FNode>('g.node').attr('opacity', (d) =>
        nodeMatchesFilter(d) ? 1 : 0.15,
    );
    sel.selectAll<SVGLineElement, FLink>('g.links line').attr('opacity', (d) => {
        const src = d.source as FNode;
        const tgt = d.target as FNode;
        return nodeMatchesFilter(src) && nodeMatchesFilter(tgt) ? 1 : 0.1;
    });
}

// ---- Data sources ----
//
// Primary: the central WebSocket pipeline pushes `topology_update` deltas via
// statesStore.topology, scoped per auth_user. We just mirror it into the
// local `nodes` ref so the existing render watch still fires.
//
// Fallback: when the WS handshake never opens (reverse proxy without WS
// support), statesStore flips `wsAvailable` to false. In that mode this
// component takes over and polls `/topology` every 15 s, the same behaviour
// as before the WS push landed.
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
                topAffectedHosts: props.flowView?.top_affected_hosts ?? null,
                servicesPerHost: props.flowView?.max_services_per_host ?? null,
            },
        );
        if (error.value) error.value = '';
    } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to load topology';
    } finally {
        loading.value = false;
    }
}

watch(
    () => statesStore.topology,
    (topo) => {
        if (!statesStore.wsAvailable) return;
        nodes.value = [...topo];
        if (error.value) error.value = '';
        loading.value = false;
    },
    { deep: false },
);

// Re-fetch and clear service cache when serviceLayout prop changes. With WS
// the topology is pushed unconditionally with services, so the layout switch
// is a pure render-side concern; we still drop cached service positions so
// the new layout starts from scratch.
watch(
    () => props.serviceLayout,
    (newVal, oldVal) => {
        for (const k of nodeCache.keys()) {
            if (k.includes('::')) nodeCache.delete(k);
        }
        if (newVal !== 'off' && oldVal === 'off') {
            for (const node of nodeCache.values()) {
                node.x = undefined;
                node.y = undefined;
                node.vx = undefined;
                node.vy = undefined;
            }
        }
        _hasFitOnce = false;
        if (!statesStore.wsAvailable) {
            fetchTopology();
        } else if (svgEl.value && nodes.value.length) {
            // Re-render immediately with the new layout. Without this the
            // user waits for the next WS topology push (up to ~15 s) before
            // anything changes on screen — feels broken.
            render(svgEl.value, nodes.value);
        }
    },
);

// Polling-fallback timer (only used when WS is unavailable). Tab-visibility
// pause keeps idle multi-tab setups from each driving their own round-trip.
function startPollTimer(): void {
    if (timer || statesStore.wsAvailable) return;
    timer = setInterval(fetchTopology, 15000);
}
function stopPollTimer(): void {
    if (timer) {
        clearInterval(timer);
        timer = null;
    }
}
function onVisibilityChange(): void {
    if (statesStore.wsAvailable) return;
    if (document.hidden) {
        stopPollTimer();
    } else {
        fetchTopology();
        startPollTimer();
    }
}

let bootstrapTimer: ReturnType<typeof setTimeout> | null = null;

onMounted(() => {
    if (statesStore.topology.length > 0) {
        nodes.value = [...statesStore.topology];
        loading.value = false;
    } else if (statesStore.wsAvailable) {
        // Wait briefly for the first WS topology_update; if none arrives,
        // fall back to a one-shot REST fetch so the user isn't stuck on a
        // blank board.
        bootstrapTimer = setTimeout(() => {
            if (!statesStore.topologyReady && nodes.value.length === 0) {
                fetchTopology();
            }
        }, 2000);
    } else {
        fetchTopology();
        if (!document.hidden) startPollTimer();
    }
    document.addEventListener('visibilitychange', onVisibilityChange);
    document.addEventListener('click', onDocumentClick);
});

watch(
    () => statesStore.wsAvailable,
    (available) => {
        if (!available) {
            fetchTopology();
            if (!document.hidden) startPollTimer();
        } else {
            stopPollTimer();
        }
    },
);

onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange);
    document.removeEventListener('click', onDocumentClick);
    if (bootstrapTimer) clearTimeout(bootstrapTimer);
    if (pendingZoomRaf !== null) {
        cancelAnimationFrame(pendingZoomRaf);
        pendingZoomRaf = null;
        pendingZoomTransform = null;
    }
    stopPollTimer();
    simulation?.stop();
    if (svgEl.value) select(svgEl.value).selectAll('*').remove();
});

// ---- D3 force types ----
interface FNode extends SimulationNodeDatum {
    id: string;
    state: string;
    output: string;
    bfsLevel: number;
    nodeType: 'host' | 'service' | 'more' | 'site';
    hostId?: string;
    siteId?: string;
    svcTotalCount?: number; // total services for this host (set on service nodes for label visibility)
    moreCount?: number; // for nodeType='more': number of services hidden behind this aggregate
    // Cached pointer to the host's TopologyNode so the tooltip can show the
    // same status detail (alias, services_summary, …) as the static board.
    // Only set on host nodes; service nodes have minimal data via their parent.
    topo?: TopologyNode;
    svc?: ServiceNode;
    parentTopo?: TopologyNode;
    // d3-force sets x/y/vx/vy
}
interface FLink extends SimulationLinkDatum<FNode> {
    source: FNode;
    target: FNode;
    sourceState: string;
    isServiceLink: boolean;
}

function boardObjectFromFNode(d: FNode): BoardObject {
    if (d.nodeType === 'site') {
        return {
            id: d.id,
            type: 'site',
            x: 0,
            y: 0,
            host_name: d.siteId ?? null,
        } as BoardObject;
    }
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

function siteHostsAggregate(siteId: string): {
    hostCount: number;
    hostsUp: number;
    hostsDown: number;
    hostsUnreachable: number;
    summary: { ok: number; warning: number; critical: number; unknown: number; pending: number };
} {
    let hostCount = 0;
    let hostsUp = 0;
    let hostsDown = 0;
    let hostsUnreachable = 0;
    const summary = { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0 };
    for (const n of nodes.value) {
        const sid = n.site_id || props.connectionId;
        if (sid !== siteId) continue;
        hostCount++;
        if (n.state === 'UP') hostsUp++;
        else if (n.state === 'DOWN') hostsDown++;
        else if (n.state === 'UNREACHABLE') hostsUnreachable++;
        const s = n.services_summary;
        if (s) {
            summary.ok += s.ok;
            summary.warning += s.warning;
            summary.critical += s.critical;
            summary.unknown += s.unknown;
            summary.pending += s.pending;
        }
    }
    return { hostCount, hostsUp, hostsDown, hostsUnreachable, summary };
}

function objectStateFromFNode(d: FNode): ObjectState {
    if (d.nodeType === 'site') {
        const agg = siteHostsAggregate(d.siteId ?? '');
        // Site state aggregation rules:
        // - DOWN: every host on this site is DOWN/UNREACHABLE (site itself is offline)
        // - CRITICAL: at least one host is DOWN/UNREACHABLE OR has critical services
        // - WARNING: at least one warning/unknown service, no criticals
        // - UP: everything is healthy
        // A single down host out of hundreds shouldn't paint the whole site
        // DOWN — that would mask the real picture during partial outages.
        const allDown = agg.hostCount > 0 && agg.hostsDown + agg.hostsUnreachable === agg.hostCount;
        const anyDown = agg.hostsDown + agg.hostsUnreachable > 0;
        const worst = allDown
            ? 'DOWN'
            : anyDown || agg.summary.critical > 0
              ? 'CRITICAL'
              : agg.summary.warning > 0 || agg.summary.unknown > 0
                ? 'WARNING'
                : 'UP';
        return {
            object_id: d.id,
            type: 'site',
            state: worst as ObjectState['state'],
            output:
                `${agg.hostCount} hosts ` +
                `(${agg.hostsUp} up, ${agg.hostsDown} down, ${agg.hostsUnreachable} unreachable)`,
            perf_data: '',
            acknowledged: false,
            in_downtime: false,
            stale: false,
            notifications_enabled: true,
            active_checks_enabled: true,
            site_id: d.siteId ?? null,
            services_summary: agg.summary,
        };
    }
    if (d.nodeType === 'service') {
        const svc = d.svc;
        const parent = d.parentTopo;
        return {
            object_id: d.id,
            type: 'service',
            state: d.state as ObjectState['state'],
            output: d.output,
            perf_data: '',
            acknowledged: svc?.acknowledged ?? false,
            in_downtime: svc?.in_downtime ?? false,
            stale: false,
            notifications_enabled: svc?.notifications_enabled ?? true,
            active_checks_enabled: parent?.active_checks_enabled ?? true,
            alias: parent?.alias,
            address: parent?.address,
            site_id: parent?.site_id ?? null,
            last_check: svc?.last_check ?? null,
            next_check: svc?.next_check ?? null,
            last_state_change: svc?.last_state_change ?? null,
            services_summary: null,
        };
    }
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
// Track last seen host id set so we can skip the (expensive) force-sim restart
// on status-only WebSocket updates. The fNode rebuild + visual attr updates
// still run, but without a sim restart there are no ticks → no DOM transform
// thrashing for hundreds of hosts on every push.
let _lastHostIds: Set<string> = new Set();
let zoomBeh: ReturnType<typeof zoom<SVGSVGElement, unknown>> | null = null;
let lastFNodes: FNode[] = [];
let _hasFitOnce = false;

// rAF-coalesce state: high-frequency wheel/drag events (e.g. trackpads firing
// >60 Hz) would otherwise write the SVG transform multiple times per frame and
// re-trigger a layout cascade on each. We capture the latest transform and
// apply it once per animation frame instead.
let pendingZoomTransform: ZoomTransform | null = null;
let pendingZoomRaf: number | null = null;
// F3 LoD: when zoomed out below this scale we hide service / "+more" nodes and
// their links — they're unreadable at that size and dominate the tick cost.
// At fit-to-view on multi-hundred-host boards the initial scale lands around
// 0.3–0.5, so 0.8 keeps the cheap host-only view active until the user zooms
// in deliberately.
const LOD_LOW_SCALE = 0.8;
let lodLow = false;
let currentZoomK = 1;

function refreshDonutWidths(): void {
    if (!svgEl.value) return;
    const arc = buildDonutArc(currentZoomK);
    const sel = select(svgEl.value);
    sel.selectAll<SVGPathElement, DonutArc>('g.donut path').attr('d', (a) => arc(a) ?? '');
    refreshHostLabelOffsets();
    refreshSiteScale();
}

// Host labels sit just outside the donut ring. Donut outer radius depends on
// the current zoom (see donutOuterRadius), so the label y offset has to track
// that — otherwise at fit-zoom-out the wide donut overlaps the hostname text
// and at zoom-in the label sits unnecessarily far away.
function refreshHostLabelOffsets(): void {
    if (!svgEl.value) return;
    const labelY = donutOuterRadius(currentZoomK) + 5;
    select(svgEl.value)
        .selectAll<SVGTextElement, FNode>('g.node text.node-label')
        .filter((d) => d.nodeType === 'host')
        .attr('y', labelY);
}

// Site root box scales up at low zoom so the label stays legible. At fit-zoom
// (k≈0.25) the 110-px-wide rect would render as ~28px without this — too
// small to read. At full zoom the scale stays 1 (no inflation).
function siteScaleForZoom(zoomK: number): number {
    const inv = 1 / Math.max(zoomK, 0.0001);
    return Math.min(3.5, Math.max(1, inv));
}
function refreshSiteScale(): void {
    if (!svgEl.value) return;
    const scale = siteScaleForZoom(currentZoomK);
    select(svgEl.value)
        .selectAll<SVGGElement, FNode>('g.node')
        .filter((d) => d.nodeType === 'site')
        .attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0}) scale(${scale})`);
}

function applyLod(): void {
    if (!svgEl.value) return;
    // Toggle a single class on the SVG root; the scoped CSS below hides
    // service / "+more" nodes and service-links via descendant selectors.
    // Inline-styling 3000+ elements per LoD flip stutters mid-zoom on
    // multi-hundred-host boards.
    svgEl.value.classList.toggle('lod-low', lodLow);
}

function flushZoomTransform(): void {
    pendingZoomRaf = null;
    if (!pendingZoomTransform || !svgEl.value) return;
    const t = pendingZoomTransform;
    pendingZoomTransform = null;
    // CSS transform on the wrapped <g> instead of the SVG `transform=`
    // attribute: Chromium/WebKit accelerate CSS transforms via the
    // compositor (GPU layer hinted with `will-change: transform`), but
    // re-rasterize the entire SVG subtree when the SVG attribute changes.
    // On 500+-host Flow boards that brings sustained pan/zoom from
    // ~14 fps to >50 fps.
    const layer = svgEl.value.querySelector('g.zoom-layer') as SVGGElement | null;
    if (layer) {
        layer.style.transform = `translate(${t.x}px, ${t.y}px) scale(${t.k})`;
    }
    const newLow = t.k < LOD_LOW_SCALE;
    if (newLow !== lodLow) {
        lodLow = newLow;
        applyLod();
    }
    currentZoomK = t.k;
    // Donut widths and host-label offsets are refreshed on zoom end, not per
    // frame — rebinding 500+ donut path d-attributes mid-zoom is the main
    // source of stutter on dense boards.
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
function fitView({ animated = true }: { animated?: boolean } = {}) {
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
    const target = zoomIdentity.translate(tx, ty).scale(scale);
    const sel = select(svg);
    if (animated) {
        sel.transition().duration(400).call(zoomBeh.transform, target);
    } else {
        sel.call(zoomBeh.transform, target);
    }
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
        // Top-K glow filter: a soft outer halo on the worst-state hosts so
        // they stand out at fit-zoom where stroke-width alone disappears.
        const defs = el.append('defs');
        const filter = defs
            .append('filter')
            .attr('id', 'top-k-glow')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%');
        filter
            .append('feGaussianBlur')
            .attr('in', 'SourceGraphic')
            .attr('stdDeviation', 3)
            .attr('result', 'blur');
        const merge = filter.append('feMerge');
        merge.append('feMergeNode').attr('in', 'blur');
        merge.append('feMergeNode').attr('in', 'blur');
        merge.append('feMergeNode').attr('in', 'SourceGraphic');

        gZoom = el.append('g').attr('class', 'zoom-layer');
        gZoom.append('g').attr('class', 'links');
        gZoom.append('g').attr('class', 'nodes');
    }

    // --- Zoom behaviour (attached once) ---
    if (!(el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached) {
        (el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached = true;
        zoomBeh = zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.15, 3])
            // Shift+drag is reserved for lasso multi-select; let the lasso
            // listener handle those events instead of panning.
            .filter((event) => {
                if (event.type === 'mousedown' && event.shiftKey) return false;
                return !event.button || event.button === 0;
            })
            // Freeze the force simulation while the user actively pans/zooms,
            // resume it on release if it still had energy left. Otherwise tick
            // handlers run alongside transform updates and the combined
            // per-frame work blows past the 16 ms budget on Fan.
            .on('start.simfreeze', () => {
                cancelPendingFit();
                simulation?.stop();
                // Disable pointer-events on the zoomed group so the browser
                // doesn't hit-test against ~3000 SVG children on every
                // pointermove. We restore on gesture end so click/hover work.
                if (svgEl.value) {
                    svgEl.value.classList.add('pan-active');
                }
            })
            .on('end.simfreeze', () => {
                if (svgEl.value) {
                    svgEl.value.classList.remove('pan-active');
                }
                if (simulation && simulation.alpha() > simulation.alphaMin()) {
                    simulation.restart();
                }
            })
            .on('end.refresh-donut', () => {
                // Reapply donut widths and host-label offsets once after the
                // zoom gesture finishes; doing it per-frame stutters at scale.
                refreshDonutWidths();
            })
            .on('zoom', (event) => {
                pendingZoomTransform = event.transform;
                if (pendingZoomRaf === null) {
                    pendingZoomRaf = requestAnimationFrame(flushZoomTransform);
                }
            });
        el.call(zoomBeh);
        attachLasso(svg);
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

    // Host nodes first. New (uncached) hosts seed their pinned position from
    // the saved board view, so reload preserves the operator's layout.
    const savedPositions = props.flowView?.positions ?? {};
    const fNodes: FNode[] = topoNodes.map((n) => {
        const cached = nodeCache.get(n.name);
        if (cached) {
            const updated: FNode = {
                ...cached,
                state: n.state,
                output: n.output,
                bfsLevel: levels.get(n.name) ?? 0,
                nodeType: 'host',
                topo: n,
            };
            nodeCache.set(n.name, updated);
            return updated;
        }
        const saved = savedPositions[n.name];
        const node: FNode = {
            id: n.name,
            state: n.state,
            output: n.output,
            bfsLevel: levels.get(n.name) ?? 0,
            nodeType: 'host',
            topo: n,
            ...(saved ? { x: saved.x, y: saved.y, fx: saved.x, fy: saved.y } : {}),
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
                    svc,
                    parentTopo: n,
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

    // Synthetic site root nodes: surface a per-site root above the host disk
    // so the operator always sees "X hosts on site Y" at a glance. Single-site
    // Checkmk setups don't tag rows with site_id (the federated multisite path
    // does), so fall back to the connection id.
    //
    // Y offset is adaptive: a flat topology (no parent chains) puts the site
    // far above the phyllotaxis disk for a clean umbrella; a hierarchical
    // topology already has its own visual root via parent_child links, so we
    // sit the site just above the topmost host to avoid a tall empty chain.
    const rootCount = topoNodes.filter((n) => n.parents.length === 0).length;
    const isMostlyFlat = topoNodes.length > 0 && rootCount / topoNodes.length >= 0.5;
    const SITE_Y_OFFSET = isMostlyFlat ? -1500 : -300;
    function siteIdFor(n: TopologyNode): string {
        return n.site_id || props.connectionId;
    }
    const siteIds: string[] = [];
    if (topoNodes.length > 0) {
        const seen = new Set<string>();
        for (const n of topoNodes) {
            const sid = siteIdFor(n);
            if (seen.has(sid)) continue;
            seen.add(sid);
            siteIds.push(sid);
        }
    }
    const siteSpread = Math.max(0, (siteIds.length - 1) * 600);
    siteIds.forEach((sid, i) => {
        const id = `__site__::${sid}`;
        const xTarget =
            siteIds.length === 1 ? 0 : -siteSpread / 2 + (i * siteSpread) / (siteIds.length - 1);
        const cached = nodeCache.get(id);
        const node: FNode = cached
            ? { ...cached, nodeType: 'site', state: 'UP', siteId: sid }
            : {
                  id,
                  state: 'UP',
                  output: '',
                  bfsLevel: 0,
                  nodeType: 'site',
                  siteId: sid,
              };
        node.fx = xTarget;
        node.fy = SITE_Y_OFFSET;
        node.x = xTarget;
        node.y = SITE_Y_OFFSET;
        nodeCache.set(id, node);
        fNodes.push(node);
    });

    // Severity-based concentric ring pre-layout for hosts that don't have
    // cached positions — gives the operator a glance-readable arrangement
    // (problems clustered toward the center) before the force simulation has
    // settled. The pre-layout positions are then used as anchors below so
    // forceX/forceY pull each host back toward its severity ring instead of
    // the simulation flattening everything into a wide ellipse.
    preLayoutHosts(fNodes.filter((n) => n.nodeType === 'host' && n.x === undefined));
    const anchorX = new Map<string, number>();
    const anchorY = new Map<string, number>();
    for (const n of fNodes) {
        if (n.nodeType !== 'host') continue;
        anchorX.set(n.id, n.x ?? 0);
        anchorY.set(n.id, n.y ?? 0);
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
    // Site-to-host links (only when synthetic site roots are active).
    // In a hierarchical topology only top-level hosts hang directly off the
    // site — child hosts already inherit a visual chain via parent_child.
    if (siteIds.length > 0) {
        const linkedHosts = isMostlyFlat
            ? topoNodes
            : topoNodes.filter((n) => n.parents.length === 0);
        for (const n of linkedHosts) {
            const src = nodeById.get(`__site__::${siteIdFor(n)}`);
            const tgt = nodeById.get(n.name);
            if (src && tgt)
                fLinks.push({
                    source: src,
                    target: tgt,
                    sourceState: 'UP',
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

    // Site-to-host links are visual only — they'd pull hosts toward the fixed
    // site root and undo the severity disk. Render them as lines but skip in
    // forceLink.
    const hostLinks = fLinks.filter(
        (l) => !l.isServiceLink && (l.source as FNode).nodeType !== 'site',
    );

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
            // Only host nodes attract/repel each other; service and "+more"
            // pseudo-nodes are positioned geometrically by the layout helpers,
            // so applying charge to them just burns ticks at O(N log N). On
            // flat topologies (no BFS hierarchy) the severity-ring pre-layout
            // already spreads hosts evenly, so charge is suppressed there —
            // otherwise the all-to-all repulsion wins against the anchor and
            // flattens the rings into a wide ellipse.
            forceManyBody<FNode>().strength((d) => {
                if (d.nodeType !== 'host') return 0;
                if (maxLvl === 0) return 0;
                const N = servicesByHost.get(d.id)?.length ?? 0;
                return N > 0 ? -Math.max(700, layoutR(N) * 9) : -600;
            }),
        )
        .force(
            'center',
            forceX<FNode>((d) => (d.nodeType === 'host' ? (anchorX.get(d.id) ?? 0) : 0)).strength(
                (d) => (d.nodeType === 'host' ? 0.18 : 0),
            ),
        )
        .force(
            'collide',
            forceCollide<FNode>((d) => {
                if (d.nodeType === 'service') return 0;
                if (d.nodeType === 'site') return 70;
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
            }).iterations(maxLvl > 0 ? 3 : 1),
        )
        .force(
            'y',
            // For real BFS hierarchies (maxLvl > 0) keep the layered look; for
            // flat topologies anchor each host to its severity-ring slot so the
            // pre-layout's glance-readable structure survives the force pass.
            maxLvl > 0
                ? forceY<FNode>((d) => (d.bfsLevel - maxLvl / 2) * vSpacing).strength((d) =>
                      d.nodeType === 'service' ? 0 : 0.4,
                  )
                : forceY<FNode>((d) =>
                      d.nodeType === 'host' ? (anchorY.get(d.id) ?? 0) : 0,
                  ).strength((d) => (d.nodeType === 'host' ? 0.18 : 0)),
        )
        // Faster alpha decay on flat boards: the severity-spiral pre-layout
        // already places hosts in their target slots, so the sim only needs
        // to resolve overlaps — 30 ticks is enough. For real BFS hierarchies
        // keep the slower decay so the layered layout has time to settle.
        .alphaDecay(maxLvl > 0 ? 0.05 : 0.1)
        .stop();

    // --- Drag behaviour ---
    const dragBehavior = drag<SVGGElement, FNode>()
        .on('start', (event, d) => {
            cancelPendingFit();
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
            if (d.nodeType === 'host') emitPinnedPositions();
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
        .attr('class', (d) => (d.isServiceLink ? 'link link-service' : 'link'))
        .attr('stroke', (d) => {
            const src = d.source as FNode;
            if (src.nodeType === 'site') return 'rgba(160,160,170,0.25)';
            return stateColor(src.state);
        })
        .attr('stroke-opacity', (d) => {
            if ((d.source as FNode).nodeType === 'site') return 0.3;
            return d.isServiceLink ? 0.3 : 0.45;
        })
        .attr('stroke-width', (d) => {
            if ((d.source as FNode).nodeType === 'site') return 0.6;
            return d.isServiceLink ? 1 : 1.5;
        })
        .attr('stroke-dasharray', (d) => {
            if ((d.source as FNode).nodeType === 'site') return '2,3';
            return d.isServiceLink ? '3,3' : null;
        });

    // --- Nodes ---
    const gNodes = gZoom.select<SVGGElement>('g.nodes');
    const nodeSel = gNodes.selectAll<SVGGElement, FNode>('g.node').data(fNodes, (d) => d.id);
    nodeSel.exit().remove();

    const nodeEnter = nodeSel
        .enter()
        .append('g')
        .attr('class', (d) => `node node-${d.nodeType}`)
        .attr('cursor', (d) => {
            if (d.nodeType === 'site') return 'pointer';
            if (d.nodeType === 'host' && !props.readonly) return 'grab';
            return props.clickAction === 'none' ? 'default' : 'pointer';
        })
        .on('click', (event: MouseEvent, d) => {
            // Site root opens an aggregated drawer; no shift-select / context
            // menu since site-level bulk ops aren't a thing.
            if (d.nodeType === 'site') {
                hoverMenu.visible = false;
                openDetail(boardObjectFromFNode(d), d);
                return;
            }
            if (props.clickAction === 'none') return;
            // Shift-click toggles multi-select. Modifier (Ctrl/Cmd) keeps the
            // legacy "open in Checkmk" behavior. Plain click opens the in-app
            // detail drawer so the operator doesn't lose context with new tabs.
            if (event.shiftKey) {
                toggleSelection(d);
                return;
            }
            if (event.ctrlKey || event.metaKey) {
                const url = buildCheckmkUrl(boardObjectFromFNode(d), props.checkmkUrl ?? null);
                if (url) openUrl(url, '_blank');
                return;
            }
            hoverMenu.visible = false;
            openDetail(boardObjectFromFNode(d), d);
        })
        .on('contextmenu', (event: MouseEvent, d) => {
            if (d.nodeType === 'site') return;
            event.preventDefault();
            hoverMenu.visible = false;
            contextMenu.object = boardObjectFromFNode(d);
            contextMenu.state = objectStateFromFNode(d);
            contextMenu.x = event.pageX;
            contextMenu.y = event.pageY;
            contextMenu.visible = true;
        })
        .on('mouseenter', (event: MouseEvent, d) => {
            if (d.nodeType === 'site') return;
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

    // Site root nodes (synthetic): rounded rect with site name.
    const siteEnter = nodeEnter.filter((d) => d.nodeType === 'site');
    const SITE_RECT_W = 110;
    const SITE_RECT_H = 36;
    siteEnter
        .append('rect')
        .attr('x', -SITE_RECT_W / 2)
        .attr('y', -SITE_RECT_H / 2)
        .attr('width', SITE_RECT_W)
        .attr('height', SITE_RECT_H)
        .attr('rx', 8)
        .attr('fill', 'var(--bg-surface)')
        .attr('stroke', 'var(--text-muted)')
        .attr('stroke-width', 1.5);
    siteEnter
        .append('text')
        .attr('class', 'type-char')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('fill', 'var(--text-muted)')
        .attr('font-size', 9)
        .attr('font-weight', '600')
        .attr('letter-spacing', '0.08em')
        .attr('pointer-events', 'none')
        .attr('y', -8)
        .text('SITE');
    siteEnter
        .append('text')
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', 13)
        .attr('font-weight', '700')
        .attr('pointer-events', 'none')
        .style('fill', 'var(--text)')
        .attr('y', 6)
        .text((d) => d.siteId ?? '');

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
        // y is recomputed by refreshHostLabelOffsets() to clear the donut ring;
        // start with the worst-case offset so the first paint never overlaps.
        .attr('y', NODE_R + DONUT_MAX_WIDTH + 5);

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
    nodeMerge
        .filter((d) => d.nodeType === 'host')
        .each(function (d) {
            const circle = (this as SVGGElement).querySelector('circle');
            if (!circle) return;
            const halo = hostHalo(d);
            circle.setAttribute('stroke', halo.stroke);
            circle.setAttribute('stroke-width', String(halo.width));
            // Top-K glow filter is anchored on the host group (not the circle)
            // so the worst-N hosts are visually unmissable even at fit-zoom
            // where stroke width alone collapses to <1 screen pixel.
            const isTopK = topKWorstIds.value.has(d.id);
            if (isTopK) {
                (this as SVGGElement).setAttribute('filter', 'url(#top-k-glow)');
            } else {
                (this as SVGGElement).removeAttribute('filter');
            }
        });

    // Donut update — bind aggregated services_summary as proportional arcs on
    // each host. Always rendered in donut layout; in fan/orbit/row only for
    // hosts whose service detail wasn't fetched (top-K cutoff in the backend),
    // so the user still sees an at-a-glance state aggregate. The exit() removes
    // leftover paths when a host transitions out of either condition.
    const donutArc = buildDonutArc(currentZoomK);
    nodeMerge
        .filter((d) => d.nodeType === 'host')
        .each(function (d) {
            // Off respects the operator's explicit choice — no automatic
            // services_omitted fallback. Donut always shows arcs. Detail
            // layouts (fan/orbit/row) fall back to donut only when the
            // backend dropped per-service rows for top-K cutoff.
            const layout = props.serviceLayout;
            const showDonut =
                layout === 'donut' || (layout !== 'off' && (d.topo?.services_omitted ?? false));
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
        if (d.nodeType === 'site') return d.siteId ?? '';
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
            .attr('transform', (d) => {
                const x = _coord(d.x);
                const y = _coord(d.y);
                if (d.nodeType === 'site') {
                    return `translate(${x},${y}) scale(${siteScaleForZoom(currentZoomK)})`;
                }
                return `translate(${x},${y})`;
            })
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
    refreshHostLabelOffsets();
    refreshSiteScale();
    applyFilterOpacity();
    applySelectionStyles();

    // F1: don't synchronously tick(250) — that blocks the main thread for
    // hundreds of ms at scale. Let the simulation converge asynchronously and
    // refine the fit once it has settled.
    const isInitial = !_hasFitOnce;
    // Compare the new host id set against the previous render to detect
    // genuine structural changes (host added/removed/renamed) vs. pure
    // status-only updates. WS push every few seconds — without this gate
    // every push restarts the force sim for 1-2s of CPU spike on 500-host
    // boards even though nothing structurally changed.
    const newHostIds = new Set<string>(topoNodes.map((n) => n.name));
    const structurallyChanged =
        newHostIds.size !== _lastHostIds.size ||
        [...newHostIds].some((id) => !_lastHostIds.has(id));
    _lastHostIds = newHostIds;

    simulation.on('tick', ticked);
    if (isInitial || structurallyChanged) {
        // Lower initial alpha on flat boards: pre-layout already approximates
        // the steady state, so 0.4 settles in ~25 ticks instead of ~75 from
        // alpha=1. Hierarchical boards still need full-energy initial sim.
        const initAlpha = isInitial ? (maxLvl > 0 ? 1 : 0.4) : 0.2;
        simulation.alpha(initAlpha).restart();
    } else {
        // Status-only update: state colors / donut segments / halos already
        // refreshed via nodeMerge above. No need to advance the sim — the
        // operator's existing layout stays put and CPU is idle until the
        // next structural change.
        simulation.stop();
    }
    if (isInitial) {
        _hasFitOnce = true;
        // Pre-layout already arranged hosts in a severity spiral, so an
        // immediate (un-animated) fit gives the operator structure on first
        // paint instead of a 4-6s wait for simulation.end.
        fitView({ animated: false });
        // Refine the fit once collide/charge have spread overlapping nodes.
        // Lower tick cap because pre-layout starts close to the steady state.
        let fitFired = false;
        const detachListeners = (): void => {
            simulation?.on('tick.fit', null);
            simulation?.on('end.fit', null);
        };
        const fireFit = (): void => {
            if (fitFired) return;
            fitFired = true;
            detachListeners();
            fitView({ animated: true });
        };
        // Operator interactions (open detail, drag, manual zoom) call this to
        // claim the current view before the refining fit can yank it.
        _cancelPendingFit = () => {
            fitFired = true;
            detachListeners();
        };
        const maxTicks = needsServices(props.serviceLayout) ? 60 : 30;
        let ticks = 0;
        simulation.on('end.fit', fireFit);
        simulation.on('tick.fit', () => {
            ticks++;
            if (ticks >= maxTicks) fireFit();
        });
    }
}
</script>

<style scoped>
/* Level-of-detail: at low zoom the service rings + "+more" badges and the
   service-links between them are unreadable, so we hide them via a single
   class on the SVG root rather than inline-styling thousands of elements. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.lod-low g.node-service),
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.lod-low g.node-more),
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.lod-low g.links line.link-service) {
    display: none;
}

/* Promote the panned/zoomed group to its own GPU-composited layer so the
   browser can re-rasterize the (large) SVG subtree once and just translate
   the layer per frame, instead of repainting all 500+ host icons +
   service rings every pan/zoom step. We feed the d3-zoom transform via the
   CSS `transform` property (not the SVG attribute) so the compositor can
   actually accelerate it, with `transform-origin: 0 0` to match the
   top-left coordinate origin SVG users expect. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(g.zoom-layer) {
    will-change: transform;
    transform-origin: 0 0;
}

/* During an active pan/zoom gesture, suppress hit-testing on the entire
   zoom-layer so pointermove doesn't traverse ~3000 SVG descendants per
   frame just to figure out hover targets the user can't interact with
   while dragging anyway. d3-zoom's start/end handlers toggle this class. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.pan-active g.zoom-layer) {
    pointer-events: none;
}

.flow-hint {
    position: absolute;
    top: calc(var(--dimension-5) + 36px);
    left: 50%;
    transform: translateX(-50%);
    z-index: 4;
    padding: 4px 10px;
    border-radius: var(--border-radius);
    background: rgb(24 24 27 / 85%);
    color: var(--text);
    font-size: 11px;
    backdrop-filter: blur(6px);
    border: 1px solid var(--border);
    pointer-events: none;
    max-width: 70%;
    text-align: center;
}

.flow-search {
    position: absolute;
    top: var(--dimension-5);
    right: var(--dimension-5);
    z-index: 6;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: var(--border-radius);
    background: rgb(24 24 27 / 85%);
    border: 1px solid var(--border);
    backdrop-filter: blur(6px);
    min-width: 200px;
}

.flow-search__input {
    flex: 1;
    min-width: 0;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text);
    font-size: 11px;
    padding: 2px 0;
}

.flow-search__input::placeholder {
    color: var(--text-muted);
}

.flow-search__clear {
    width: 16px;
    height: 16px;
    line-height: 14px;
    text-align: center;
    border-radius: 50%;
    background: var(--bg-hover);
    color: var(--text-muted);
    border: none;
    cursor: pointer;
    font-size: 14px;
    padding: 0;
}

.flow-search__clear:hover {
    color: var(--text);
}

.flow-search__toggle {
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    background: transparent;
    color: var(--text-muted);
    border: 1px solid transparent;
    cursor: pointer;
    padding: 0;
}

.flow-search__toggle:hover {
    color: var(--text);
    background: var(--bg-hover);
}

.flow-search__toggle--active {
    color: var(--color-yellow-50, #fbbf24);
    border-color: var(--color-yellow-50, #fbbf24);
    background: rgb(251 191 36 / 12%);
}

.bulk-actions {
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 6;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    box-shadow: 0 6px 24px rgb(0 0 0 / 40%);
}

.bulk-actions__count {
    font-size: 12px;
    font-weight: var(--font-weight-semibold);
    color: var(--text);
    margin-right: 4px;
}

.bulk-actions__btn {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    padding: 4px 10px;
    font-size: 11px;
    cursor: pointer;
}

.bulk-actions__btn:hover {
    background: var(--bg-hover);
}

.bulk-actions__btn--clear {
    width: 24px;
    padding: 0;
    text-align: center;
    color: var(--text-muted);
}
</style>
