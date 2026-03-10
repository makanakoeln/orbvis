<template>
  <!-- Textbox -->
  <div
    v-if="object.type === 'textbox'"
    class="px-2.5 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap pointer-events-none ring-1 transition-all"
    :class="selected
      ? 'ring-indigo-400 bg-[var(--bg-glass)] text-[var(--text)]'
      : 'ring-[var(--border)] bg-[var(--bg-glass)] text-zinc-200'"
    style="backdrop-filter: blur(4px)"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    {{ object.label_text || 'Text' }}
  </div>

  <!-- Gadget -->
  <div
    v-else-if="object.view_type === 'gadget'"
    class="flex flex-col items-center"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <div :class="selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950 rounded-xl' : ''">
      <GadgetRenderer
        :type="object.gadget_type || 'gauge'"
        :metric="object.gadget_metric"
        :state="state"
        :size="iconSize"
      />
    </div>
    <div v-if="object.label_show"
      class="mt-1 font-medium whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
      :style="labelStyle">
      {{ displayName }}
    </div>
  </div>

  <!-- All other types: icon circle (or custom image) + label -->
  <div
    v-else
    class="flex flex-col items-center"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <!-- Icon with badges -->
    <div class="relative">
      <!-- Custom icon image -->
      <img
        v-if="object.icon"
        :src="`/icons/${object.icon}`"
        :style="iconStyle"
        class="object-contain transition-all duration-300"
        :class="selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950 rounded' : ''"
      />
      <!-- State circle (fallback) -->
      <div
        v-else
        class="rounded-full flex items-center justify-center transition-colors duration-300"
        :class="[stateClass, selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950' : '', pulseClass]"
        :style="iconStyle"
      >
        <span class="text-white leading-none select-none" :style="charStyle">{{ typeChar }}</span>
      </div>
      <!-- Badges only shown for state circle, not custom icons -->
      <!-- Acknowledged badge -->
      <span
        v-if="state?.acknowledged"
        class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-400 text-zinc-900 flex items-center justify-center leading-none shadow-sm"
        title="Acknowledged"
        style="font-size: 8px; font-weight: 900"
      >✓</span>
      <!-- Downtime badge -->
      <span
        v-if="state?.in_downtime"
        class="absolute -top-1 -left-1 w-4 h-4 rounded-full bg-blue-400 text-zinc-900 flex items-center justify-center leading-none shadow-sm"
        title="In downtime"
        style="font-size: 8px; font-weight: 900"
      >⏸</span>
    </div>
    <!-- Label -->
    <div
      v-if="object.label_show"
      class="mt-1.5 font-medium whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
      :style="labelStyle"
    >
      {{ displayName }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MapObject, ObjectState } from '@/types/api'
import GadgetRenderer from './GadgetRenderer.vue'

const props = defineProps<{
  object: MapObject
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
}>()

defineEmits<{
  hover: [event: MouseEvent]
  'hover-leave': []
  'context-menu': [event: MouseEvent]
}>()

const iconStyle = computed(() => ({
  width: `${props.iconSize}px`,
  height: `${props.iconSize}px`,
}))

const charStyle = computed(() => {
  const chars = typeChar.value.length
  const factor = chars === 1 ? 0.46 : 0.30
  return {
    fontSize: `${Math.max(10, Math.round(props.iconSize * factor))}px`,
    fontWeight: '900',
    textShadow: '0 1px 2px rgba(0,0,0,0.4)',
  }
})

const STATE_CLASSES: Record<string, string> = {
  UP: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]',
  OK: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]',
  DOWN: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
  CRITICAL: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
  UNREACHABLE: 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.4)]',
  UNKNOWN: 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.4)]',
  WARNING: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]',
  PENDING: 'bg-zinc-500',
}

const stateClass = computed(() => {
  const s = props.state?.state ?? 'PENDING'
  return STATE_CLASSES[s] ?? STATE_CLASSES['PENDING']
})

const PULSE_STATES = new Set(['DOWN', 'CRITICAL', 'UNREACHABLE'])
const pulseClass = computed(() =>
  PULSE_STATES.has(props.state?.state ?? '') ? 'state-pulse' : ''
)

const TYPE_CHARS: Record<string, string> = {
  host: 'H', service: 'S', hostgroup: 'HG', servicegroup: 'SG',
  map: 'M', shape: '◆', line: '—',
}
const typeChar = computed(() => TYPE_CHARS[props.object.type] ?? '?')

const labelStyle = computed(() => ({
  fontSize: `${props.object.label_size ?? 11}px`,
  color: props.object.label_color ?? '#e4e4e7',
  background: props.object.label_background && props.object.label_background !== 'transparent'
    ? props.object.label_background
    : 'rgba(9,9,11,0.75)',
  backdropFilter: 'blur(4px)',
  textShadow: '0 1px 3px rgba(0,0,0,0.8)',
}))

const displayName = computed(() => {
  if (props.object.label_text) return props.object.label_text
  if (props.object.type === 'host') return props.object.host_name ?? props.object.id
  if (props.object.type === 'service') return props.object.service_description ?? props.object.id
  if (props.object.type === 'map') return props.object.map_name ?? props.object.id
  if (props.object.group_name) return props.object.group_name
  return props.object.id
})
</script>

<style scoped>
@keyframes state-pulse {
  0%, 100% { box-shadow: 0 0 6px 1px rgba(239, 68, 68, 0.5); }
  50%       { box-shadow: 0 0 18px 4px rgba(239, 68, 68, 0.85); }
}
.state-pulse {
  animation: state-pulse 1.8s ease-in-out infinite;
}
</style>
