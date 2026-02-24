<template>
  <div
    class="fixed z-50 bg-gray-900 border border-gray-600 rounded-lg shadow-xl p-3 text-sm min-w-48 pointer-events-none"
    :style="{ left: `${x}px`, top: `${y}px` }"
  >
    <div class="font-semibold mb-1">{{ displayName }}</div>
    <div class="text-xs text-gray-400 mb-1">{{ object.type }}</div>
    <div v-if="state" class="flex items-center gap-2">
      <span class="w-2 h-2 rounded-full inline-block" :class="stateColor"></span>
      <span :class="stateTextColor">{{ state.state }}</span>
    </div>
    <div v-if="state?.output" class="text-xs text-gray-400 mt-1 max-w-xs truncate">
      {{ state.output }}
    </div>
    <div v-if="state?.acknowledged" class="text-xs text-yellow-400 mt-1">✓ Acknowledged</div>
    <div v-if="state?.in_downtime" class="text-xs text-blue-400 mt-1">⏸ In downtime</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MapObject, ObjectState } from '@/types/api'

const props = defineProps<{
  object: MapObject
  state: ObjectState | undefined
  x: number
  y: number
}>()

const displayName = computed(() => {
  if (props.object.label_text) return props.object.label_text
  if (props.object.host_name && props.object.service_description)
    return `${props.object.host_name} / ${props.object.service_description}`
  return props.object.host_name ?? props.object.group_name ?? props.object.id
})

const STATE_BG: Record<string, string> = {
  UP: 'bg-green-400', OK: 'bg-green-400',
  DOWN: 'bg-red-500', CRITICAL: 'bg-red-500',
  UNREACHABLE: 'bg-orange-400', UNKNOWN: 'bg-orange-400',
  WARNING: 'bg-yellow-400',
  PENDING: 'bg-gray-400',
}
const STATE_TEXT: Record<string, string> = {
  UP: 'text-green-400', OK: 'text-green-400',
  DOWN: 'text-red-400', CRITICAL: 'text-red-400',
  UNREACHABLE: 'text-orange-400', UNKNOWN: 'text-orange-400',
  WARNING: 'text-yellow-400',
  PENDING: 'text-gray-400',
}

const stateColor = computed(() => STATE_BG[props.state?.state ?? 'PENDING'] ?? 'bg-gray-400')
const stateTextColor = computed(() => STATE_TEXT[props.state?.state ?? 'PENDING'] ?? 'text-gray-400')
</script>
