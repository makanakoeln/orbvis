<template>
  <div
    ref="canvasEl"
    class="relative select-none bg-[var(--bg)]"
    :class="[placing ? 'cursor-crosshair' : '', bgImageSize ? 'w-full h-full' : '']"
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
    <svg
      class="absolute inset-0 w-full h-full"
      :viewBox="bgImageSize ? `0 0 ${bgImageSize.width} ${bgImageSize.height}` : undefined"
      :preserveAspectRatio="bgImageSize ? 'none' : undefined"
    >
      <BoardLine
        v-for="line in lineObjects"
        :key="line.id"
        :object="line"
        :state="states[line.id]"
        :edit-mode="editMode"
        :drag-coords="lineDragPositions[line.id]"
        @line-drag-start="(evt, mode) => $emit('line-drag-start', evt, line, mode)"
        @context-menu="(evt) => onObjectContextMenu(evt, line)"
        @line-click="onLineClick(line)"
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
        :backend-id="config.backend_id"
        @hover="!editMode && openHoverMenu($event, obj)"
        @hover-leave="!editMode && closeHoverMenu()"
        @graph-resize-start="onGraphResizeStart($event, obj)"
      />
    </div>

    <!-- Hover popup -->
    <HoverMenu
      v-if="hoverMenu.visible && hoverMenu.object"
      :object="hoverMenu.object"
      :state="states[hoverMenu.object.id]"
      :x="hoverMenu.x"
      :y="hoverMenu.y"
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
      @force-check="onContextMenuForceCheck"
      @add-comment="onContextMenuAddComment"
      @enable-notifications="onContextMenuToggleNotifications(true)"
      @disable-notifications="onContextMenuToggleNotifications(false)"
      @enable-checks="onContextMenuToggleChecks(true)"
      @disable-checks="onContextMenuToggleChecks(false)"
    />
  </div>

  <!-- ACK modal -->
  <AckModal
    v-if="ackModalObject && checkmkUrl"
    :object="ackModalObject"
    :checkmk-url="checkmkUrl"
    @close="ackModalObject = null"
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
    @close="downtimeModalObject = null"
  />
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { cmkApi } from '@/api/client';
import { useToast } from '@/composables/useToast';
import { useSettingsStore } from '@/stores/settings';
import type { BoardConfig, BoardObject as BoardObjectType, ObjectState } from '@/types/api';
import { resolveTemplate } from '@/utils/template';

import AckModal from './AckModal.vue';
import BoardLine from './BoardLine.vue';
import BoardObject from './BoardObject.vue';
import CommentModal from './CommentModal.vue';
import ContextMenu from './ContextMenu.vue';
import DowntimeModal from './DowntimeModal.vue';
import HoverMenu from './HoverMenu.vue';

const { t } = useI18n();
const toast = useToast();
const settingsStore = useSettingsStore();

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

const router = useRouter();
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

const canvasWidth = computed(() =>
  props.config.objects.reduce(
    (m, o) => Math.max(m, o.x + (o.type === 'graph' ? (o.graph_width ?? 400) : 150)),
    800,
  ),
);
const canvasHeight = computed(() =>
  props.config.objects.reduce(
    (m, o) => Math.max(m, o.y + (o.type === 'graph' ? (o.graph_height ?? 200) : 150)),
    600,
  ),
);

// Canvas style: with background → fill parent absolutely; without → fixed pixel size
const canvasStyle = computed(() => {
  const bg = props.config.background_image;
  const url = bgImageUrl.value;
  const pixelSize = {
    minWidth: `max(${canvasWidth.value}px, 100%)`,
    minHeight: `max(${canvasHeight.value}px, 100%)`,
  };
  if (bg && bgImageSize.value) {
    return {
      backgroundImage: `url(${url})`,
      backgroundRepeat: 'no-repeat',
      backgroundSize: '100% 100%',
    };
  }
  if (bg && !bgImageFailed.value) {
    // Image still loading — reserve pixel space so SVG overlay doesn't collapse
    return {
      ...pixelSize,
      backgroundImage: `url(${url})`,
      backgroundRepeat: 'no-repeat',
      backgroundSize: '100% 100%',
    };
  }
  return pixelSize;
});

const nonLineObjects = computed(() => props.config.objects.filter((o) => o.type !== 'line'));
const lineObjects = computed(() => props.config.objects.filter((o) => o.type === 'line'));

function objectWrapperStyle(obj: BoardObjectType) {
  const pos = localDragPositions[obj.id] ?? { x: obj.x, y: obj.y };
  const isMap = obj.type === 'map';
  const canDrag = props.editMode || props.isAdmin;
  const cursor = canDrag
    ? _dragId.value === obj.id
      ? 'grabbing'
      : 'grab'
    : isMap || obj.url || !!buildCheckmkUrl(obj)
      ? 'pointer'
      : 'default';
  const zIndex = _dragId.value === obj.id ? 100 : (obj.z ?? 1);

  if (bgImageSize.value) {
    // Percentage positions relative to native image dimensions
    return {
      left: `${(pos.x / bgImageSize.value.width) * 100}%`,
      top: `${(pos.y / bgImageSize.value.height) * 100}%`,
      transform: 'translate(-50%, -50%)',
      cursor,
      zIndex,
    };
  }
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

function buildCheckmkUrl(obj: BoardObjectType): string | null {
  const base = props.checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
  if (!base) return null;
  const parts = base.split('/');
  const site = parts[parts.length - 1] || null;
  const p: Record<string, string> = {};
  if (site) p.site = site;

  if (obj.type === 'host' && obj.host_name) {
    p.view_name = 'hoststatus';
    p.host = obj.host_name;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
  }
  if (obj.type === 'service' && obj.host_name && obj.service_description) {
    p.view_name = 'service';
    p.host = obj.host_name;
    p.service = obj.service_description;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
  }
  if (obj.type === 'hostgroup' && obj.group_name) {
    p.view_name = 'hostgroup';
    p.hostgroup = obj.group_name;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
  }
  if (obj.type === 'servicegroup' && obj.group_name) {
    p.view_name = 'servicegroup';
    p.servicegroup = obj.group_name;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
  }
  return null;
}

function onLineClick(line: BoardObjectType) {
  if (props.editMode) emit('object-click', line);
}

function _openUrl(url: string, target: string) {
  // Use a real <a> click so the browser doesn't treat it as a popup (important
  // when OrbVis runs inside a Checkmk iframe — window.open gets popup-blocked).
  const a = document.createElement('a');
  a.href = url;
  a.target = target;
  a.rel = 'noreferrer';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function onObjectClick(obj: BoardObjectType, event?: MouseEvent) {
  if (props.editMode) {
    if (!_didMove.value) emit('object-click', obj, event);
    return;
  }
  // Suppress navigation click if the pointer just completed a real drag move
  if (_didMove.value) return;
  if (obj.url) {
    _openUrl(obj.url, obj.url_target || '_blank');
    return;
  }
  if (obj.type === 'map' && obj.map_name) {
    router.push({ name: 'board', params: { name: obj.map_name } });
    return;
  }
  const cmkUrl = buildCheckmkUrl(obj);
  if (cmkUrl) {
    _openUrl(cmkUrl, '_blank');
  }
}

function onObjectContextMenu(event: MouseEvent, obj: BoardObjectType) {
  if (props.editMode) {
    // Get the bounding rect of the clicked element (wrapper div or SVG element)
    const el = (event.currentTarget ?? event.target) as Element | null;
    const r = el?.getBoundingClientRect?.();
    const anchor =
      r && (r.width > 0 || r.height > 0)
        ? { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
        : { left: event.clientX, top: event.clientY, right: event.clientX, bottom: event.clientY };
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
  x: 0,
  y: 0,
});
const contextMenu = reactive({
  visible: false,
  object: null as BoardObjectType | null,
  x: 0,
  y: 0,
});

function openHoverMenu(event: MouseEvent, obj: BoardObjectType) {
  hoverMenu.object = obj;
  hoverMenu.x = event.pageX + 12;
  hoverMenu.y = event.pageY + 12;
  hoverMenu.visible = true;
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

const ackModalObject = ref<BoardObjectType | null>(null);
const downtimeModalObject = ref<BoardObjectType | null>(null);
const commentModalObject = ref<BoardObjectType | null>(null);

function onContextMenuAck() {
  const obj = contextMenu.object;
  closeMenus();
  if (obj) ackModalObject.value = obj;
}

function onContextMenuDowntime() {
  const obj = contextMenu.object;
  closeMenus();
  if (obj) downtimeModalObject.value = obj;
}

function onContextMenuAddComment() {
  const obj = contextMenu.object;
  closeMenus();
  if (obj) commentModalObject.value = obj;
}

async function onContextMenuRemoveAck() {
  const obj = contextMenu.object;
  closeMenus();
  if (!obj || !props.checkmkUrl) return;
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      await cmkApi.removeAcknowledgementService(
        props.checkmkUrl,
        obj.host_name,
        obj.service_description,
      );
    } else if (obj.host_name) {
      await cmkApi.removeAcknowledgementHost(props.checkmkUrl, obj.host_name);
    }
  } catch {
    toast.error(t('contextMenu.removeAckFailed'));
  }
}

async function onContextMenuToggleNotifications(enable: boolean) {
  const obj = contextMenu.object;
  closeMenus();
  if (!obj || !props.checkmkUrl) return;
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      await (enable ? cmkApi.enableNotificationsService : cmkApi.disableNotificationsService)(
        props.checkmkUrl,
        obj.host_name,
        obj.service_description,
      );
    } else if (obj.host_name) {
      await (enable ? cmkApi.enableNotificationsHost : cmkApi.disableNotificationsHost)(
        props.checkmkUrl,
        obj.host_name,
      );
    }
  } catch {
    toast.error(t('contextMenu.toggleNotificationsFailed'));
  }
}

async function onContextMenuToggleChecks(enable: boolean) {
  const obj = contextMenu.object;
  closeMenus();
  if (!obj || !props.checkmkUrl) return;
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      await (enable ? cmkApi.enableChecksService : cmkApi.disableChecksService)(
        props.checkmkUrl,
        obj.host_name,
        obj.service_description,
      );
    } else if (obj.host_name) {
      await (enable ? cmkApi.enableChecksHost : cmkApi.disableChecksHost)(
        props.checkmkUrl,
        obj.host_name,
      );
    }
  } catch {
    toast.error(t('contextMenu.toggleChecksFailed'));
  }
}

async function onContextMenuForceCheck() {
  const obj = contextMenu.object;
  closeMenus();
  if (!obj || !props.checkmkUrl) return;
  try {
    if (obj.type === 'service' && obj.host_name && obj.service_description) {
      await cmkApi.forceCheckService(props.checkmkUrl, obj.host_name, obj.service_description);
    } else if (obj.host_name) {
      await cmkApi.forceCheckHost(props.checkmkUrl, obj.host_name);
    }
  } catch {
    toast.error(t('contextMenu.forceCheckFailed'));
  }
}

function closeMenus() {
  hoverMenu.visible = false;
  contextMenu.visible = false;
}

function getMapPosition(event: MouseEvent): { x: number; y: number } {
  if (!canvasEl.value) return { x: 0, y: 0 };
  const rect = canvasEl.value.getBoundingClientRect();
  if (bgImageSize.value) {
    // Canvas fills container — convert screen coords to native image coords
    return {
      x: ((event.clientX - rect.left) / rect.width) * bgImageSize.value.width,
      y: ((event.clientY - rect.top) / rect.height) * bgImageSize.value.height,
    };
  }
  const parent = canvasEl.value.parentElement!;
  return {
    x: event.clientX - rect.left + parent.scrollLeft,
    y: event.clientY - rect.top + parent.scrollTop,
  };
}

defineExpose({ getCanvasEl: () => canvasEl.value, getMapPosition });
</script>
