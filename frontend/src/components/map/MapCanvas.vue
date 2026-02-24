<template>
  <div
    ref="canvasEl"
    class="relative w-full h-full overflow-auto select-none"
    :style="backgroundStyle"
    @click.self="closeMenus"
  >
    <!-- SVG overlay for lines -->
    <svg
      class="absolute inset-0 pointer-events-none"
      :width="canvasWidth"
      :height="canvasHeight"
    >
      <MapLine
        v-for="line in lineObjects"
        :key="line.id"
        :object="line"
        :state="states[line.id]"
      />
    </svg>

    <!-- Map objects (icons/labels) -->
    <MapObject
      v-for="obj in nonLineObjects"
      :key="obj.id"
      :object="obj"
      :state="states[obj.id]"
      :icon-size="config.globals.icon_size"
      @context-menu="openContextMenu($event, obj)"
      @hover="openHoverMenu($event, obj)"
      @hover-leave="closeHoverMenu"
    />

    <!-- Hover popup -->
    <HoverMenu
      v-if="hoverMenu.visible && hoverMenu.object"
      :object="hoverMenu.object"
      :state="states[hoverMenu.object.id]"
      :x="hoverMenu.x"
      :y="hoverMenu.y"
    />

    <!-- Context menu -->
    <ContextMenu
      v-if="contextMenu.visible && contextMenu.object"
      :object="contextMenu.object"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @close="closeMenus"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive } from 'vue'
import type { MapConfig, MapObject as MapObjectType, ObjectState } from '@/types/api'
import MapObject from './MapObject.vue'
import MapLine from './MapLine.vue'
import HoverMenu from './HoverMenu.vue'
import ContextMenu from './ContextMenu.vue'

const props = defineProps<{
  config: MapConfig
  states: Record<string, ObjectState>
}>()

const canvasEl = ref<HTMLDivElement | null>(null)
const canvasWidth = computed(() => 2000)
const canvasHeight = computed(() => 2000)

const backgroundStyle = computed(() => {
  const bg = props.config.globals.background_image
  if (!bg) return {}
  return {
    backgroundImage: `url(/maps/backgrounds/${bg})`,
    backgroundRepeat: 'no-repeat',
    backgroundSize: 'contain',
  }
})

const nonLineObjects = computed(() =>
  props.config.objects.filter((o) => o.type !== 'line')
)

const lineObjects = computed(() =>
  props.config.objects.filter((o) => o.type === 'line')
)

// ---- Menus ----
const hoverMenu = reactive({ visible: false, object: null as MapObjectType | null, x: 0, y: 0 })
const contextMenu = reactive({ visible: false, object: null as MapObjectType | null, x: 0, y: 0 })

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
  event.preventDefault()
  contextMenu.object = obj
  contextMenu.x = event.pageX
  contextMenu.y = event.pageY
  contextMenu.visible = true
}

function closeMenus() {
  hoverMenu.visible = false
  contextMenu.visible = false
}
</script>
