<template>
    <div
        ref="canvasEl"
        class="relative select-none bg-[var(--bg)]"
        :class="placing ? 'cursor-crosshair' : ''"
        :style="canvasStyle"
        :data-native-width="bgImageSize?.width"
        :data-native-height="bgImageSize?.height"
        @click="onCanvasClick"
        @pointermove.prevent="onCanvasPointerMove"
        @pointerup="onCanvasPointerUp"
        @pointercancel="onCanvasPointerUp"
    >
        <!-- Grid overlay — always in CSS pixel space so it's visible regardless of bg-image scale -->
        <svg
            v-if="editMode && (snapGrid ?? 0) > 0"
            class="absolute inset-0 w-full h-full pointer-events-none"
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

        <!-- SVG overlay for lines -->
        <svg class="absolute inset-0 w-full h-full">
            <BoardLine
                v-for="line in lineObjects"
                :key="line.id"
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
        </svg>

        <!-- Map objects: each wrapped in a positioned div -->
        <div
            v-for="obj in nonLineObjects"
            :key="obj.id"
            class="absolute"
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
                    (obj.display?.mode === 'gadget' ? 60 : (iconSizeOverride ?? config.icon_size))
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
import { computed, reactive, ref, watch } from 'vue';

import { useObjectActions } from '@/composables/useObjectActions';
import { useSettingsStore } from '@/stores/settings';
import { useStatesStore } from '@/stores/states';
import type { BoardConfig, BoardObject as BoardObjectType, ObjectState } from '@/types/api';
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
}>();

const emit = defineEmits<{
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
    const base: Record<string, string> = {
        minWidth: `max(${canvasWidth.value}px, 100%)`,
        minHeight: `max(${canvasHeight.value}px, 100%)`,
    };
    if (color) base.backgroundColor = color;
    if (bg && !bgImageFailed.value) {
        base.backgroundImage = `url(${url})`;
        base.backgroundRepeat = 'no-repeat';
        base.backgroundSize = 'auto';
        base.backgroundPosition = 'top left';
    }
    return base;
});

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

    return {
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        transform: 'translate(-50%, -50%)',
        cursor,
        zIndex,
    };
}

// ---- Pointer-capture drag handlers ----

function onObjectPointerDown(event: PointerEvent, obj: BoardObjectType) {
    if (event.button === 2) return; // right-click: let contextmenu event fire normally
    _suppressNextCanvasClick.value = false;
    if (!props.editMode) return;
    event.preventDefault();
    const canvas = canvasEl.value;
    if (!canvas) return;
    canvas.setPointerCapture(event.pointerId);
    const rect = canvas.getBoundingClientRect();
    _dragOffX.value = event.clientX - rect.left - obj.x;
    _dragOffY.value = event.clientY - rect.top - obj.y;
    _dragInitX.value = obj.x;
    _dragInitY.value = obj.y;
    _didMove.value = false;
    _dragId.value = obj.id;
    localDragPositions[obj.id] = { x: obj.x, y: obj.y };
    if (props.editMode) emit('object-click', obj); // select on pointerdown (no event = no action bar)
}

function onGraphResizeStart(event: PointerEvent, obj: BoardObjectType) {
    if (!canvasEl.value) return;
    canvasEl.value.setPointerCapture(event.pointerId);
    _resizeId.value = obj.id;
    _resizeInitW.value = obj.graph_width ?? 400;
    _resizeInitH.value = obj.graph_height ?? 200;
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
    const x = Math.max(0, _snap(Math.round(event.clientX - rect.left - _dragOffX.value)));
    const y = Math.max(0, _snap(Math.round(event.clientY - rect.top - _dragOffY.value)));
    if (
        !_didMove.value &&
        (Math.abs(x - _dragInitX.value) > 4 || Math.abs(y - _dragInitY.value) > 4)
    ) {
        _didMove.value = true;
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
    if (props.editMode) {
        // Get the bounding rect of the clicked element (wrapper div or SVG element)
        const el = (event.currentTarget ?? event.target) as Element | null;
        const r = el?.getBoundingClientRect?.();
        const anchor =
            r && (r.width > 0 || r.height > 0)
                ? { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
                : {
                      left: event.clientX,
                      top: event.clientY,
                      right: event.clientX,
                      bottom: event.clientY,
                  };
        emit('object-contextmenu', obj, anchor);
    } else {
        openContextMenu(event, obj);
    }
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
    return {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
    };
}

defineExpose({ getCanvasEl: () => canvasEl.value, getMapPosition });
</script>
