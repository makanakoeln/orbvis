<template>
  <div
    class="absolute flex flex-col items-center cursor-pointer"
    :style="positionStyle"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <!-- Icon -->
    <div
      class="rounded-full border-2 flex items-center justify-center"
      :class="stateClass"
      :style="iconStyle"
    >
      <span class="text-xs font-bold">{{ typeChar }}</span>
    </div>
    <!-- Label -->
    <div
      v-if="object.label_show"
      class="mt-1 text-xs text-white bg-black/60 px-1 rounded whitespace-nowrap"
    >
      {{ displayName }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MapObject, ObjectState } from '@/types/api'

const props = defineProps<{
  object: MapObject
  state: ObjectState | undefined
  iconSize: number
}>()

defineEmits<{
  hover: [event: MouseEvent]
  'hover-leave': []
  'context-menu': [event: MouseEvent]
}>()

const positionStyle = computed(() => ({
  left: `${props.object.x}px`,
  top: `${props.object.y}px`,
  transform: 'translate(-50%, -50%)',
}))

const iconStyle = computed(() => ({
  width: `${props.iconSize}px`,
  height: `${props.iconSize}px`,
}))

const STATE_CLASSES: Record<string, string> = {
  UP: 'border-green-400 bg-green-900',
  OK: 'border-green-400 bg-green-900',
  DOWN: 'border-red-500 bg-red-900',
  CRITICAL: 'border-red-500 bg-red-900',
  UNREACHABLE: 'border-orange-400 bg-orange-900',
  UNKNOWN: 'border-orange-400 bg-orange-900',
  WARNING: 'border-yellow-400 bg-yellow-900',
  PENDING: 'border-gray-400 bg-gray-700',
}

const stateClass = computed(() => {
  const s = props.state?.state ?? 'PENDING'
  return STATE_CLASSES[s] ?? STATE_CLASSES['PENDING']
})

const TYPE_CHARS: Record<string, string> = {
  host: 'H',
  service: 'S',
  hostgroup: 'HG',
  servicegroup: 'SG',
  map: 'M',
  shape: '◆',
  textbox: 'T',
}

const typeChar = computed(() => TYPE_CHARS[props.object.type] ?? '?')

const displayName = computed(() => {
  if (props.object.label_text) return props.object.label_text
  if (props.object.type === 'host') return props.object.host_name ?? props.object.id
  if (props.object.type === 'service') return props.object.service_description ?? props.object.id
  if (props.object.group_name) return props.object.group_name
  return props.object.id
})
</script>
