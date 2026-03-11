<template>
  <div
    ref="canvasEl"
    class="relative select-none bg-[var(--bg)]"
    :class="[placing ? 'cursor-crosshair' : '', bgImageSize ? 'w-full h-full' : '']"
    :style="canvasStyle"
    :data-native-width="bgImageSize?.width"
    :data-native-height="bgImageSize?.height"
    @click="onCanvasClick"
  >
    <!-- SVG overlay for grid + lines -->
    <svg
      class="absolute top-0 left-0"
      :width="bgImageSize ? '100%' : canvasWidth"
      :height="bgImageSize ? '100%' : canvasHeight"
      :viewBox="bgImageSize ? `0 0 ${bgImageSize.width} ${bgImageSize.height}` : undefined"
      :preserveAspectRatio="bgImageSize ? 'none' : undefined"
    >
      <!-- Grid crosshairs (edit mode only) -->
      <template v-if="editMode && (snapGrid ?? 0) > 0">
        <defs>
          <pattern :id="`grid-${snapGrid}`" :width="snapGrid" :height="snapGrid" patternUnits="userSpaceOnUse">
            <line x1="0" y1="-4" x2="0" y2="4" stroke="rgba(99,102,241,0.55)" stroke-width="1" />
            <line x1="-4" y1="0" x2="4" y2="0" stroke="rgba(99,102,241,0.55)" stroke-width="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" :fill="`url(#grid-${snapGrid})`" />
      </template>

      <MapLine
        v-for="line in lineObjects"
        :key="line.id"
        :object="line"
        :state="states[line.id]"
        :edit-mode="editMode"
        :drag-coords="lineDragPositions[line.id]"
        @line-drag-start="(evt, mode) => $emit('line-drag-start', evt, line, mode)"
        @context-menu="(evt) => onObjectContextMenu(evt, line)"
      />
    </svg>

    <!-- Map objects: each wrapped in a positioned div -->
    <div
      v-for="obj in nonLineObjects"
      :key="obj.id"
      class="absolute"
      :style="objectWrapperStyle(obj)"
      @mousedown.prevent="onObjectMouseDown($event, obj)"
      @click.stop="onObjectClick(obj)"
      @contextmenu.prevent="onObjectContextMenu($event, obj)"
    >
      <MapObject
        :object="obj"
        :state="states[obj.id]"
        :icon-size="obj.icon_size ?? (obj.view_type === 'gadget' ? 60 : (iconSizeOverride ?? config.globals.icon_size))"
        :selected="selectedObjectId === obj.id"
        @hover="!editMode && openHoverMenu($event, obj)"
        @hover-leave="!editMode && closeHoverMenu()"
      />
    </div>

    <!-- Hover popup -->
    <HoverMenu
      v-if="hoverMenu.visible && hoverMenu.object"
      :object="hoverMenu.object"
      :state="states[hoverMenu.object.id]"
      :x="hoverMenu.x"
      :y="hoverMenu.y"
      :template="resolveTemplate(hoverMenu.object.hover_template, props.config.globals.hover_template, settingsStore.settings.hover_template)"
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
      :template="resolveTemplate(contextMenu.object.context_template, props.config.globals.context_template, settingsStore.settings.context_template)"
      @close="closeMenus"
      @edit="onContextMenuEdit"
      @delete="onContextMenuDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { MapConfig, MapObject as MapObjectType, ObjectState } from '@/types/api'
import { resolveTemplate } from '@/utils/template'
import { useSettingsStore } from '@/stores/settings'
import MapObject from './MapObject.vue'
import MapLine from './MapLine.vue'
import HoverMenu from './HoverMenu.vue'
import ContextMenu from './ContextMenu.vue'

const settingsStore = useSettingsStore()

const props = defineProps<{
  config: MapConfig
  states: Record<string, ObjectState>
  editMode: boolean
  placing: boolean
  draggingId: string | null
  dragPositions: Record<string, { x: number; y: number }>
  lineDragPositions: Record<string, { x: number; y: number; x2: number; y2: number }>
  selectedObjectId: string | null
  checkmkUrl?: string | null
  iconSizeOverride?: number
  isAdmin?: boolean
  snapGrid?: number
}>()

const emit = defineEmits<{
  'object-mousedown': [event: MouseEvent, obj: MapObjectType]
  'object-click': [obj: MapObjectType]
  'object-contextmenu': [obj: MapObjectType]
  'object-delete': [obj: MapObjectType]
  'line-drag-start': [event: MouseEvent, obj: MapObjectType, mode: 'move' | 'start' | 'end']
  'canvas-click': [event: MouseEvent]
}>()

const router = useRouter()
const canvasEl = ref<HTMLDivElement | null>(null)
const bgImageSize = ref<{ width: number; height: number } | null>(null)

watch(
  () => props.config.globals.background_image,
  (bg) => {
    if (!bg) { bgImageSize.value = null; return }
    const img = new Image()
    img.onload = () => { bgImageSize.value = { width: img.naturalWidth, height: img.naturalHeight } }
    img.src = `${import.meta.env.BASE_URL}maps/backgrounds/${bg}`
  },
  { immediate: true },
)

const canvasWidth = computed(() =>
  props.config.objects.reduce((m, o) => Math.max(m, o.x + 150), 800),
)
const canvasHeight = computed(() =>
  props.config.objects.reduce((m, o) => Math.max(m, o.y + 150), 600),
)

// Canvas style: with background → fill parent absolutely; without → fixed pixel size
const canvasStyle = computed(() => {
  const bg = props.config.globals.background_image
  if (bg && bgImageSize.value) {
    return {
      backgroundImage: `url(${import.meta.env.BASE_URL}maps/backgrounds/${bg})`,
      backgroundRepeat: 'no-repeat',
      backgroundSize: '100% 100%',
    }
  }
  if (bg) {
    // Image still loading — fill with background color, reveal once size known
    return {
      backgroundImage: `url(${import.meta.env.BASE_URL}maps/backgrounds/${bg})`,
      backgroundRepeat: 'no-repeat',
      backgroundSize: '100% 100%',
    }
  }
  return {
    width: `${canvasWidth.value}px`,
    minHeight: `${canvasHeight.value}px`,
  }
})

const nonLineObjects = computed(() =>
  props.config.objects.filter((o) => o.type !== 'line'),
)
const lineObjects = computed(() =>
  props.config.objects.filter((o) => o.type === 'line'),
)

function objectWrapperStyle(obj: MapObjectType) {
  const pos = props.dragPositions[obj.id] ?? { x: obj.x, y: obj.y }
  const isMap = obj.type === 'map'
  const cursor = props.editMode
    ? (props.draggingId === obj.id ? 'grabbing' : 'grab')
    : (isMap || obj.url || !!buildCheckmkUrl(obj) ? 'pointer' : 'default')
  const zIndex = props.draggingId === obj.id ? 100 : (obj.z ?? 1)

  if (bgImageSize.value) {
    // Percentage positions relative to native image dimensions
    return {
      left: `${(pos.x / bgImageSize.value.width) * 100}%`,
      top: `${(pos.y / bgImageSize.value.height) * 100}%`,
      transform: 'translate(-50%, -50%)',
      cursor,
      zIndex,
    }
  }
  return {
    left: `${pos.x}px`,
    top: `${pos.y}px`,
    transform: 'translate(-50%, -50%)',
    cursor,
    zIndex,
  }
}

// ---- Event delegation ----

function onObjectMouseDown(event: MouseEvent, obj: MapObjectType) {
  if (props.editMode) {
    emit('object-mousedown', event, obj)
  }
}

function buildCheckmkUrl(obj: MapObjectType): string | null {
  const base = props.checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '')
  if (!base) return null
  const parts = base.split('/')
  const site = parts[parts.length - 1] || null
  const p: Record<string, string> = {}
  if (site) p.site = site

  if ((obj.type === 'host') && obj.host_name) {
    p.view_name = 'hoststatus'; p.host = obj.host_name
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`
  }
  if (obj.type === 'service' && obj.host_name && obj.service_description) {
    p.view_name = 'service'; p.host = obj.host_name; p.service = obj.service_description
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`
  }
  if (obj.type === 'hostgroup' && obj.group_name) {
    p.view_name = 'hostgroup'; p.hostgroup = obj.group_name
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`
  }
  if (obj.type === 'servicegroup' && obj.group_name) {
    p.view_name = 'servicegroup'; p.servicegroup = obj.group_name
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`
  }
  return null
}

function onObjectClick(obj: MapObjectType) {
  if (props.editMode) {
    emit('object-click', obj)
    return
  }
  if (obj.url) {
    window.open(obj.url, obj.url_target || '_blank')
    return
  }
  if (obj.type === 'map' && obj.map_name) {
    router.push({ name: 'map', params: { name: obj.map_name } })
    return
  }
  const cmkUrl = buildCheckmkUrl(obj)
  if (cmkUrl) {
    window.open(cmkUrl, '_blank')
  }
}

function onObjectContextMenu(event: MouseEvent, obj: MapObjectType) {
  if (props.editMode) {
    emit('object-contextmenu', obj)
  } else {
    openContextMenu(event, obj)
  }
}

function onCanvasClick(event: MouseEvent) {
  closeMenus()
  emit('canvas-click', event)
}

// ---- Hover / Context menus (view mode only) ----

const hoverMenu = reactive({
  visible: false,
  object: null as MapObjectType | null,
  x: 0, y: 0,
})
const contextMenu = reactive({
  visible: false,
  object: null as MapObjectType | null,
  x: 0, y: 0,
})

function openHoverMenu(event: MouseEvent, obj: MapObjectType) {
  hoverMenu.object = obj
  hoverMenu.x = event.pageX + 12
  hoverMenu.y = event.pageY + 12
  hoverMenu.visible = true
}

function closeHoverMenu() {
  hoverMenu.visible = false
}

function openContextMenu(event: MouseEvent, obj: MapObjectType) {
  contextMenu.object = obj
  contextMenu.x = event.pageX
  contextMenu.y = event.pageY
  contextMenu.visible = true
}

function onContextMenuEdit() {
  const obj = contextMenu.object
  closeMenus()
  if (obj) emit('object-contextmenu', obj)
}

function onContextMenuDelete() {
  const obj = contextMenu.object
  closeMenus()
  if (obj) emit('object-delete', obj)
}

function closeMenus() {
  hoverMenu.visible = false
  contextMenu.visible = false
}

function getMapPosition(event: MouseEvent): { x: number; y: number } {
  if (!canvasEl.value) return { x: 0, y: 0 }
  const rect = canvasEl.value.getBoundingClientRect()
  if (bgImageSize.value) {
    // Canvas fills container — convert screen coords to native image coords
    return {
      x: ((event.clientX - rect.left) / rect.width) * bgImageSize.value.width,
      y: ((event.clientY - rect.top) / rect.height) * bgImageSize.value.height,
    }
  }
  const parent = canvasEl.value.parentElement!
  return {
    x: event.clientX - rect.left + parent.scrollLeft,
    y: event.clientY - rect.top + parent.scrollTop,
  }
}

defineExpose({ canvasEl, getMapPosition })
</script>
