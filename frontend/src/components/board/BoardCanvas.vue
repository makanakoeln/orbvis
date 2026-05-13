<template>
    <div
        ref="canvasEl"
        class="relative select-none bg-[var(--bg)]"
        :class="placing ? 'cursor-crosshair' : ''"
        :style="canvasStyle"
        :data-native-width="canvasWidth"
        :data-native-height="canvasHeight"
        @click="onCanvasClick"
        @pointermove.prevent="onCanvasPointerMove"
        @pointerup="onCanvasPointerUp"
        @pointercancel="onCanvasPointerUp"
        @wheel="onCanvasWheel"
    >
        <!-- Grid overlay — viewBox keeps coords in native canvas space so the
             snap intervals match drag-quantised object positions even after
             the canvas asymmetric-stretches into the pane. -->
        <svg
            v-if="editMode && (snapGrid ?? 0) > 0"
            class="absolute inset-0 w-full h-full pointer-events-none"
            :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
            preserveAspectRatio="none"
        >
            <defs>
                <pattern
                    :id="`grid-${snapGrid}`"
                    :width="snapGrid"
                    :height="snapGrid"
                    patternUnits="userSpaceOnUse"
                >
                    <path
                        :d="`M ${snapGrid} 0 L 0 0 0 ${snapGrid}`"
                        fill="none"
                        stroke="rgba(99,102,241,0.6)"
                        stroke-width="1"
                    />
                </pattern>
            </defs>
            <rect width="100%" height="100%" :fill="`url(#grid-${snapGrid})`" />
        </svg>

        <!-- SVG overlay for lines. Renders at display-pixel coords (no
             viewBox) so strokes, polygon arrowheads, and text labels keep
             their natural proportions when the canvas asymmetric-stretches.
             BoardLine multiplies its native obj.x/y by the injected
             `canvasScale` so endpoints still align with HTML object icons. -->
        <svg class="absolute inset-0 w-full h-full">
            <g
                v-for="line in lineObjects"
                :key="line.id"
                :style="{
                    opacity: matchesSearch(line) ? 1 : 0.25,
                    transition: 'opacity 120ms ease',
                }"
            >
                <BoardLine
                    :object="line"
                    :state="states[line.id]"
                    :edit-mode="editMode"
                    :drag-coords="lineDragPositions[line.id]"
                    :connection-id="config.connection_id"
                    @line-drag-start="(evt, mode) => $emit('line-drag-start', evt, line, mode)"
                    @context-menu="(evt) => onObjectContextMenu(evt, line)"
                    @line-click="onLineClick(line)"
                    @hover="openHoverMenu($event, line)"
                    @hover-leave="closeHoverMenu()"
                />
            </g>
        </svg>

        <!-- Map objects: each wrapped in a positioned div -->
        <div
            v-for="obj in nonLineObjects"
            :key="obj.id"
            class="absolute"
            :data-object-id="obj.id"
            :style="objectWrapperStyle(obj)"
            @pointerdown="onObjectPointerDown($event, obj)"
            @dragstart.prevent
            @click.stop="onObjectClick(obj, $event)"
            @dblclick.stop="emit('object-dblclick', obj)"
            @contextmenu.prevent="onObjectContextMenu($event, obj)"
        >
            <BoardObject
                :object="obj"
                :state="states[obj.id]"
                :icon-size="
                    obj.display?.image_size ??
                    (obj.display?.mode === 'gadget'
                        ? 60
                        : (iconSizeOverride ??
                          config.icon_size ??
                          settingsStore.settings.icon_size))
                "
                :selected="selectedObjectId === obj.id"
                :edit-mode="editMode"
                :resize-override="localResizeDimensions[obj.id]"
                :connection-id="config.connection_id"
                @hover="!editMode && openHoverMenu($event, obj)"
                @hover-leave="!editMode && closeHoverMenu()"
                @graph-resize-start="onGraphResizeStart($event, obj)"
                @subtree-enter="
                    (subObj, subState, evt) => !editMode && openSubtreeHover(evt, subObj, subState)
                "
                @subtree-leave="!editMode && closeHoverMenu()"
            />
        </div>

        <!-- Zoom indicator + reset (only visible when zoomed). Teleported to
             <body> so it escapes the canvas's CSS `zoom` (which would otherwise
             scale this fixed-positioned pill along with the rest). -->
        <Teleport to="body">
            <button
                v-if="userZoom !== 1 && !editMode"
                type="button"
                class="board-zoom-reset"
                title="Reset to fit"
                @click="resetZoom"
            >
                {{ Math.round(userZoom * 100) }}% ↺
            </button>
        </Teleport>

        <!-- Hover popup -->
        <HoverMenu
            v-if="hoverMenu.visible && hoverMenu.object"
            :object="hoverMenu.object"
            :state="hoverMenu.stateOverride ?? states[hoverMenu.object.id]"
            :x="hoverMenu.x"
            :y="hoverMenu.y"
            :anchor-rect="hoverMenu.anchorRect"
            :connection-id="props.config.connection_id"
            :template="
                resolveTemplate(
                    hoverMenu.object.hover_template,
                    props.config.hover_template,
                    settingsStore.settings.hover_template,
                )
            "
        />

        <!-- Context menu -->
        <ContextMenu
            v-if="contextMenu.visible && contextMenu.object"
            :object="contextMenu.object"
            :state="states[contextMenu.object.id]"
            :x="contextMenu.x"
            :y="contextMenu.y"
            :checkmk-url="checkmkUrl"
            :show-edit="isAdmin"
            :template="
                resolveTemplate(
                    contextMenu.object.context_template,
                    props.config.context_template,
                    settingsStore.settings.context_template,
                )
            "
            @close="closeMenus"
            @edit="onContextMenuEdit"
            @duplicate="onContextMenuDuplicate"
            @delete="onContextMenuDelete"
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

    <!-- ACK modal -->
    <AckModal
        v-if="ackModalObject && checkmkUrl"
        :object="ackModalObject"
        :checkmk-url="checkmkUrl"
        @close="
            ackModalObject = null;
            statesStore.refreshAfterCommand();
        "
    />

    <!-- Comment modal -->
    <CommentModal
        v-if="commentModalObject && checkmkUrl"
        :object="commentModalObject"
        :checkmk-url="checkmkUrl"
        @close="commentModalObject = null"
    />

    <!-- Downtime modal -->
    <DowntimeModal
        v-if="downtimeModalObject && checkmkUrl"
        :object="downtimeModalObject"
        :checkmk-url="checkmkUrl"
        @close="
            downtimeModalObject = null;
            statesStore.refreshAfterCommand();
        "
    />

    <!-- Remove downtime modal (multiple downtimes) -->
    <RemoveDowntimeModal
        v-if="removeDowntimeModal.visible && checkmkUrl"
        :downtimes="removeDowntimeModal.downtimes"
        :checkmk-url="checkmkUrl"
        :object-name="removeDowntimeModal.objectName"
        @close="
            removeDowntimeModal.visible = false;
            statesStore.refreshAfterCommand();
        "
    />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue';

import { useObjectActions } from '@/composables/useObjectActions';
import { useSettingsStore } from '@/stores/settings';
import { useStatesStore } from '@/stores/states';
import type { BoardConfig, BoardObject as BoardObjectType, ObjectState } from '@/types/api';
import { objectMatchesFilter } from '@/utils/objectFilter';
import { resolveTemplate } from '@/utils/template';

import AckModal from './AckModal.vue';
import BoardLine from './BoardLine.vue';
import BoardObject from './BoardObject.vue';
import CommentModal from './CommentModal.vue';
import ContextMenu from './ContextMenu.vue';
import DowntimeModal from './DowntimeModal.vue';
import HoverMenu from './HoverMenu.vue';
import RemoveDowntimeModal from './RemoveDowntimeModal.vue';

const settingsStore = useSettingsStore();
const statesStore = useStatesStore();

const props = defineProps<{
    config: BoardConfig;
    states: Record<string, ObjectState>;
    editMode: boolean;
    placing: boolean;
    lineDragPositions: Record<string, { x: number; y: number; x2: number; y2: number }>;
    selectedObjectId: string | null;
    checkmkUrl?: string | null;
    iconSizeOverride?: number;
    isAdmin?: boolean;
    snapGrid?: number;
    /**
     * Search needle from the top-level board search bar. Non-matching objects
     * dim to 25% so the operator's eye snaps to matches without losing the
     * spatial layout — same approach as FlowBoard's filter.
     */
    filterNeedle?: string;
}>();

const emit = defineEmits<{
    'object-drag-start': [id: string];
    'object-drag-end': [id: string, x: number, y: number];
    'object-click': [obj: BoardObjectType, event?: MouseEvent];
    'object-contextmenu': [
        obj: BoardObjectType,
        anchor: { left: number; top: number; right: number; bottom: number } | null,
    ];
    'object-dblclick': [obj: BoardObjectType];
    'object-delete': [obj: BoardObjectType];
    'object-duplicate': [obj: BoardObjectType];
    'line-drag-start': [event: MouseEvent, obj: BoardObjectType, mode: 'move' | 'start' | 'end'];
    'canvas-click': [event: MouseEvent];
    'graph-resize-end': [id: string, width: number, height: number];
}>();

const canvasEl = ref<HTMLDivElement | null>(null);
const bgImageSize = ref<{ width: number; height: number } | null>(null);

// Local pointer-capture drag state
const _dragId = ref<string | null>(null);
const _dragObj = ref<BoardObjectType | null>(null);
const _dragPointerId = ref<number | null>(null);
const _dragOffX = ref(0);
const _dragOffY = ref(0);
const _dragInitX = ref(0);
const _dragInitY = ref(0);
const _didMove = ref(false);
const localDragPositions = reactive<Record<string, { x: number; y: number }>>({});
// When the user taps an object (no drag, no placing), pointer capture redirects
// the synthetic click to the canvas div. Suppress that canvas-click so it doesn't
// deselect the just-selected object.
const _suppressNextCanvasClick = ref(false);

// Graph resize state
const _resizeId = ref<string | null>(null);
const _resizeInitW = ref(0);
const _resizeInitH = ref(0);
const _resizeStartX = ref(0);
const _resizeStartY = ref(0);
const localResizeDimensions = reactive<Record<string, { width: number; height: number }>>({});

function _snap(v: number): number {
    if (!props.snapGrid) return v;
    return Math.round(v / props.snapGrid) * props.snapGrid;
}

const bgImageFailed = ref(false);
const bgImageCacheKey = ref(Date.now());

const bgImageUrl = computed(() => {
    const bg = props.config.background_image;
    if (!bg) return null;
    return `${import.meta.env.BASE_URL}boards/backgrounds/${bg}?v=${bgImageCacheKey.value}`;
});

watch(
    () => props.config.background_image,
    (bg) => {
        bgImageFailed.value = false;
        bgImageCacheKey.value = Date.now();
        if (!bg) {
            bgImageSize.value = null;
            return;
        }
        const img = new Image();
        img.onload = () => {
            bgImageSize.value = { width: img.naturalWidth, height: img.naturalHeight };
        };
        img.onerror = () => {
            bgImageFailed.value = true;
            bgImageSize.value = null;
        };
        img.src = bgImageUrl.value!;
    },
    { immediate: true },
);

const canvasWidth = computed(() => {
    const fromObjects = props.config.objects.reduce(
        (m, o) => Math.max(m, o.x + (o.type === 'graph' ? (o.graph_width ?? 400) : 150)),
        800,
    );
    return Math.max(fromObjects, bgImageSize.value?.width ?? 0);
});
const canvasHeight = computed(() => {
    const fromObjects = props.config.objects.reduce(
        (m, o) => Math.max(m, o.y + (o.type === 'graph' ? (o.graph_height ?? 200) : 150)),
        600,
    );
    return Math.max(fromObjects, bgImageSize.value?.height ?? 0);
});

const canvasStyle = computed(() => {
    const bg = props.config.background_image;
    const url = bgImageUrl.value;
    const color = props.config.background_color;
    // At userZoom=1 the canvas fills the pane (asymmetric stretch — operators
    // want the wallpaper look). At userZoom>1 it switches to native pixel
    // size so CSS zoom can scale bg + objects together; coverFactor keeps the
    // first zoom step visually close to the stretched default so the aspect
    // snap at z=1→1.01 is as small as possible.
    const base: Record<string, string> =
        userZoom.value === 1
            ? { width: '100%', height: '100%' }
            : {
                  width: `${canvasWidth.value}px`,
                  height: `${canvasHeight.value}px`,
                  zoom: String(coverFactor.value * userZoom.value),
              };
    if (color) base.backgroundColor = color;
    if (bg && !bgImageFailed.value) {
        // Stretch the image to fill the canvas. Canvas dimensions already
        // expand to encompass both the natural image size and the object
        // extent (whichever is larger), so 100% 100% never squashes the
        // image below its natural size for fresh boards designed at native
        // bg dimensions, and faithfully covers the full object extent for
        // boards from 0.1.0 where object coords were saved in the
        // stretched-canvas coordinate system.
        base.backgroundImage = `url(${url})`;
        base.backgroundRepeat = 'no-repeat';
        base.backgroundSize = '100% 100%';
    }
    return base;
});

// ZOOM_MIN=1 so operators cannot zoom out below "bg fills pane" — that view
// has no informational value for monitoring.
const ZOOM_MIN = 1;
const ZOOM_MAX = 4;
const userZoom = ref(1);

const coverFactor = computed(() => {
    const pane = paneSize.value;
    if (!pane.width || !pane.height) return 1;
    if (!canvasWidth.value || !canvasHeight.value) return 1;
    const fx = pane.width / canvasWidth.value;
    const fy = pane.height / canvasHeight.value;
    return Math.max(fx, fy);
});

function onCanvasWheel(event: WheelEvent): void {
    // ctrl+wheel = zoom (matches browsers' image-viewer / map convention).
    // Bare wheel keeps the outer container's natural scroll behaviour.
    // Edit mode is fixed at user_zoom=1 so drag-coord math stays simple.
    if (props.editMode || !event.ctrlKey) return;
    event.preventDefault();
    const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1;
    const next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, userZoom.value * factor));
    if (next === userZoom.value) return;
    // Anchor zoom around the cursor: scroll the outer container so the point
    // under the mouse stays under the mouse after the size change.
    const outer = findScrollAncestor(canvasEl.value);
    if (outer) {
        const rect = canvasEl.value!.getBoundingClientRect();
        const cx = event.clientX - rect.left;
        const cy = event.clientY - rect.top;
        const ratio = next / userZoom.value;
        userZoom.value = next;
        requestAnimationFrame(() => {
            outer.scrollLeft += cx * (ratio - 1);
            outer.scrollTop += cy * (ratio - 1);
        });
    } else {
        userZoom.value = next;
    }
}

function resetZoom(): void {
    userZoom.value = 1;
}

// canvasScale feeds child SVG layers (lines, arrows, line labels) that draw
// in display-px so their stroke widths and glyph shapes don't distort under
// the asymmetric bg-image stretch at zoom=1.
const canvasDisplaySize = ref<{ width: number; height: number }>({ width: 0, height: 0 });
const canvasScale = computed(() => ({
    sx: canvasWidth.value > 0 ? canvasDisplaySize.value.width / canvasWidth.value : 1,
    sy: canvasHeight.value > 0 ? canvasDisplaySize.value.height / canvasHeight.value : 1,
}));
provide('canvasScale', canvasScale);
const paneSize = ref<{ width: number; height: number }>({ width: 0, height: 0 });
let canvasResizeObserver: ResizeObserver | null = null;
let paneResizeObserver: ResizeObserver | null = null;

function setIfChanged(
    target: { value: { width: number; height: number } },
    width: number,
    height: number,
): void {
    if (target.value.width !== width || target.value.height !== height) {
        target.value = { width, height };
    }
}

onMounted(() => {
    const el = canvasEl.value;
    if (!el) return;
    canvasDisplaySize.value = { width: el.clientWidth, height: el.clientHeight };
    const pane = findScrollAncestor(el);
    if (pane) paneSize.value = { width: pane.clientWidth, height: pane.clientHeight };
    if (typeof ResizeObserver === 'undefined') return;
    canvasResizeObserver = new ResizeObserver((entries) => {
        const entry = entries[0];
        if (!entry) return;
        const box = entry.contentBoxSize?.[0];
        const w = box ? box.inlineSize : el.clientWidth;
        const h = box ? box.blockSize : el.clientHeight;
        setIfChanged(canvasDisplaySize, w, h);
    });
    canvasResizeObserver.observe(el);
    if (pane) {
        paneResizeObserver = new ResizeObserver(() => {
            setIfChanged(paneSize, pane.clientWidth, pane.clientHeight);
        });
        paneResizeObserver.observe(pane);
    }
});
onBeforeUnmount(() => {
    canvasResizeObserver?.disconnect();
    canvasResizeObserver = null;
    paneResizeObserver?.disconnect();
    paneResizeObserver = null;
});

function findScrollAncestor(el: HTMLElement | null): HTMLElement | null {
    let node: HTMLElement | null = el?.parentElement ?? null;
    while (node) {
        const overflow = getComputedStyle(node).overflow;
        if (/(auto|scroll)/.test(overflow)) return node;
        node = node.parentElement;
    }
    return null;
}

watch(
    () => props.editMode,
    (edit) => {
        if (edit) userZoom.value = 1;
    },
);

const nonLineObjects = computed(() => props.config.objects.filter((o) => o.type !== 'line'));
const lineObjects = computed(() => props.config.objects.filter((o) => o.type === 'line'));

function objectWrapperStyle(obj: BoardObjectType) {
    const pos = localDragPositions[obj.id] ?? { x: obj.x, y: obj.y };
    const canDrag = props.editMode || props.isAdmin;
    const clickable = props.config.click_action !== 'none';
    const cursor = canDrag
        ? _dragId.value === obj.id
            ? 'grabbing'
            : 'grab'
        : clickable
          ? 'pointer'
          : 'default';
    const zIndex = _dragId.value === obj.id ? 100 : (obj.z ?? 1);
    // % positioning anchors the object to a fraction of the native coord
    // space; combined with bg-image at 100% 100%, the object stays on the
    // same bg-pixel regardless of how the canvas is scaled to fit the pane.
    const w = canvasWidth.value || 1;
    const h = canvasHeight.value || 1;
    return {
        left: `${(pos.x / w) * 100}%`,
        top: `${(pos.y / h) * 100}%`,
        transform: 'translate(-50%, -50%)',
        cursor,
        zIndex,
        opacity: matchesSearch(obj) ? 1 : 0.25,
        transition: 'opacity 120ms ease',
    };
}

function matchesSearch(obj: BoardObjectType): boolean {
    return objectMatchesFilter(obj, props.filterNeedle ?? '');
}

// ---- Pointer-capture drag handlers ----

// Translate a viewport-px coord (event.clientX/Y minus canvas rect.left/top)
// into the canvas's native coord space — the asymmetric-stretch canvas means
// 1px on screen != 1px in obj.x. Used by every drag/resize/place handler.
function viewportToNative(viewportX: number, viewportY: number, rect: DOMRect) {
    const sx = (canvasWidth.value || 1) / Math.max(rect.width, 1);
    const sy = (canvasHeight.value || 1) / Math.max(rect.height, 1);
    return { x: viewportX * sx, y: viewportY * sy };
}

function onObjectPointerDown(event: PointerEvent, obj: BoardObjectType) {
    if (event.button === 2) return; // right-click: let contextmenu event fire normally
    _suppressNextCanvasClick.value = false;
    if (!props.editMode) return;
    const canvas = canvasEl.value;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const cursorNative = viewportToNative(
        event.clientX - rect.left,
        event.clientY - rect.top,
        rect,
    );
    _dragOffX.value = cursorNative.x - obj.x;
    _dragOffY.value = cursorNative.y - obj.y;
    _dragInitX.value = obj.x;
    _dragInitY.value = obj.y;
    _didMove.value = false;
    _dragId.value = obj.id;
    _dragObj.value = obj;
    _dragPointerId.value = event.pointerId;
    localDragPositions[obj.id] = { x: obj.x, y: obj.y };
}

function onGraphResizeStart(event: PointerEvent, obj: BoardObjectType) {
    if (!canvasEl.value) return;
    canvasEl.value.setPointerCapture(event.pointerId);
    _resizeId.value = obj.id;
    if (obj.type === 'textbox') {
        // For ``auto``-sized textboxes (no stored width/height) start the
        // resize from what the user actually sees on screen.
        const handle = event.target as HTMLElement | null;
        const rect = handle?.parentElement?.getBoundingClientRect();
        _resizeInitW.value = obj.textbox_width ?? Math.round(rect?.width ?? 200);
        _resizeInitH.value = obj.textbox_height ?? Math.round(rect?.height ?? 40);
    } else {
        _resizeInitW.value = obj.graph_width ?? 400;
        _resizeInitH.value = obj.graph_height ?? 200;
    }
    _resizeStartX.value = event.clientX;
    _resizeStartY.value = event.clientY;
    localResizeDimensions[obj.id] = { width: _resizeInitW.value, height: _resizeInitH.value };
}

function onCanvasPointerMove(event: PointerEvent) {
    // Handle graph resize
    const rid = _resizeId.value;
    if (rid) {
        const w = Math.max(50, _resizeInitW.value + (event.clientX - _resizeStartX.value));
        const h = Math.max(30, _resizeInitH.value + (event.clientY - _resizeStartY.value));
        localResizeDimensions[rid] = { width: Math.round(w), height: Math.round(h) };
        return;
    }

    const id = _dragId.value;
    if (!id || !canvasEl.value) return;
    const rect = canvasEl.value.getBoundingClientRect();
    const cursorNative = viewportToNative(
        event.clientX - rect.left,
        event.clientY - rect.top,
        rect,
    );
    const x = Math.max(0, _snap(Math.round(cursorNative.x - _dragOffX.value)));
    const y = Math.max(0, _snap(Math.round(cursorNative.y - _dragOffY.value)));
    if (
        !_didMove.value &&
        (Math.abs(x - _dragInitX.value) > 4 || Math.abs(y - _dragInitY.value) > 4)
    ) {
        _didMove.value = true;
        if (_dragPointerId.value !== null && canvasEl.value) {
            try {
                canvasEl.value.setPointerCapture(_dragPointerId.value);
            } catch {
                // pointer may have ended between pointerdown and first move
            }
        }
        emit('object-drag-start', id);
    }
    localDragPositions[id] = { x, y };
}

function onCanvasPointerUp(event: PointerEvent) {
    // Finalize graph resize
    const rid = _resizeId.value;
    if (rid) {
        _resizeId.value = null;
        const dims = localResizeDimensions[rid];
        delete localResizeDimensions[rid];
        if (dims) emit('graph-resize-end', rid, dims.width, dims.height);
        return;
    }

    const id = _dragId.value;
    _dragId.value = null;
    _dragObj.value = null;
    _dragPointerId.value = null;

    if (!id) {
        if (props.placing) emit('canvas-click', event as unknown as MouseEvent);
        return;
    }
    const pos = localDragPositions[id];
    delete localDragPositions[id];
    if (_didMove.value && pos) {
        emit('object-drag-end', id, pos.x, pos.y);
    } else if (!_didMove.value && props.placing) {
        emit('canvas-click', event as unknown as MouseEvent);
    } else if (!_didMove.value) {
        // No drag — native click/dblclick will fire on the object div and
        // route through @click.stop / @dblclick.stop handlers. Just suppress
        // the bubbling canvas-click so it doesn't deselect.
        _suppressNextCanvasClick.value = true;
    }
}

// ---- Event delegation ----

function onLineClick(line: BoardObjectType) {
    if (props.editMode) {
        emit('object-click', line);
        return;
    }
    // In view mode lines navigate the same way icons do (URL → CMK view).
    onObjectClick(line);
}

function onObjectClick(obj: BoardObjectType, event?: MouseEvent) {
    // Suppress navigation click if the pointer just completed a real drag move
    if (_didMove.value) return;
    closeMenus();
    emit('object-click', obj, event);
}

function onObjectContextMenu(event: MouseEvent, obj: BoardObjectType) {
    openContextMenu(event, obj);
}

function onCanvasClick(event: MouseEvent) {
    if (_suppressNextCanvasClick.value) {
        _suppressNextCanvasClick.value = false;
        return;
    }
    closeMenus();
    emit('canvas-click', event);
}

// ---- Hover / Context menus (view mode only) ----

const hoverMenu = reactive({
    visible: false,
    object: null as BoardObjectType | null,
    // Override state for synthetic objects (BI subtree nodes) that aren't in `states`.
    stateOverride: null as ObjectState | null,
    x: 0,
    y: 0,
    anchorRect: null as { left: number; top: number; right: number; bottom: number } | null,
});
const contextMenu = reactive({
    visible: false,
    object: null as BoardObjectType | null,
    x: 0,
    y: 0,
});

function openHoverMenu(event: MouseEvent, obj: BoardObjectType) {
    hoverMenu.object = obj;
    hoverMenu.stateOverride = null;
    hoverMenu.x = event.pageX + 12;
    hoverMenu.y = event.pageY + 12;
    // Walk up from event.target to find an icon-sized wrapper for anchoring
    // the tooltip flip. Skipped for lines because their bounding-box spans
    // the whole board. event.currentTarget would be null by now (cleared
    // after Vue's emit bridge), so we work from event.target instead.
    hoverMenu.anchorRect = obj.type === 'line' ? null : findIconWrapperRect(event.target);
    hoverMenu.visible = true;
}

function openSubtreeHover(event: MouseEvent, obj: BoardObjectType, state: ObjectState) {
    hoverMenu.object = obj;
    hoverMenu.stateOverride = state;
    hoverMenu.x = event.pageX + 12;
    hoverMenu.y = event.pageY + 12;
    hoverMenu.anchorRect = findIconWrapperRect(event.target);
    hoverMenu.visible = true;
}

function findIconWrapperRect(
    target: EventTarget | null,
): { left: number; top: number; right: number; bottom: number } | null {
    let el = target instanceof Element ? target : null;
    while (el && el !== document.body) {
        const r = el.getBoundingClientRect();
        // Icon wrappers are roughly square and small — a real icon plus its
        // label tops out around 100×100 px. Anything larger is a container.
        if (r.width > 0 && r.width < 200 && r.height > 0 && r.height < 200) {
            return { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
        }
        el = el.parentElement;
    }
    return null;
}

function closeHoverMenu() {
    hoverMenu.visible = false;
}

function openContextMenu(event: MouseEvent, obj: BoardObjectType) {
    if (props.states[obj.id]?.state === 'NO_PERMISSION') return;
    contextMenu.object = obj;
    contextMenu.x = event.pageX;
    contextMenu.y = event.pageY;
    contextMenu.visible = true;
}

function onContextMenuEdit() {
    const obj = contextMenu.object;
    const x = contextMenu.x;
    const y = contextMenu.y;
    closeMenus();
    if (obj) emit('object-contextmenu', obj, { left: x, top: y, right: x, bottom: y });
}

function onContextMenuDelete() {
    const obj = contextMenu.object;
    closeMenus();
    if (obj) emit('object-delete', obj);
}

function onContextMenuDuplicate() {
    const obj = contextMenu.object;
    closeMenus();
    if (obj) emit('object-duplicate', obj);
}

// ---- CMK actions from context menu ----

const objectActions = useObjectActions(() => props.checkmkUrl ?? null, closeMenus);
const { ackModalObject, downtimeModalObject, commentModalObject, removeDowntimeModal } =
    objectActions;
const onContextMenuAck = () => objectActions.handlers.acknowledge(contextMenu.object);
const onContextMenuRemoveAck = () => objectActions.handlers.removeAck(contextMenu.object);
const onContextMenuDowntime = () => objectActions.handlers.scheduleDowntime(contextMenu.object);
const onContextMenuRemoveDowntime = () => objectActions.handlers.removeDowntime(contextMenu.object);
const onContextMenuAddComment = () => objectActions.handlers.addComment(contextMenu.object);
const onContextMenuToggleNotifications = (enable: boolean) =>
    objectActions.handlers.toggleNotifications(contextMenu.object, enable);

const onContextMenuForceCheck = () => objectActions.handlers.forceCheck(contextMenu.object);

function closeMenus() {
    hoverMenu.visible = false;
    contextMenu.visible = false;
}

function getMapPosition(event: MouseEvent): { x: number; y: number } {
    if (!canvasEl.value) return { x: 0, y: 0 };
    const rect = canvasEl.value.getBoundingClientRect();
    return viewportToNative(event.clientX - rect.left, event.clientY - rect.top, rect);
}

defineExpose({ getCanvasEl: () => canvasEl.value, getMapPosition, resetZoom });
</script>

<style scoped>
.board-zoom-reset {
    /* Sits left of the BoardSearch filter (top:5 right:5 inside the canvas
       wrapper, ≈ 200 px wide). Vertical 48 px clears the 36 px topbar. */
    position: fixed;
    top: 48px;
    right: calc(var(--dimension-5) + 215px);
    z-index: 6;
    padding: 6px 14px;
    border-radius: var(--border-radius);
    background: rgb(24 24 27 / 85%);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    backdrop-filter: blur(6px);
}

.board-zoom-reset:hover {
    border-color: var(--color-corporate-green-50);
}
</style>
