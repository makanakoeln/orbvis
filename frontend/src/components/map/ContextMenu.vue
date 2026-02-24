<template>
  <div
    class="fixed z-50 bg-gray-900 border border-gray-600 rounded-lg shadow-xl py-1 min-w-40"
    :style="{ left: `${x}px`, top: `${y}px` }"
  >
    <div class="px-3 py-1 text-xs text-gray-500 border-b border-gray-700">
      {{ object.type }}: {{ displayName }}
    </div>
    <button
      class="w-full text-left px-3 py-2 text-sm hover:bg-gray-700 text-gray-200"
      @click="openInMonitoring"
    >Open in monitoring</button>
    <button
      class="w-full text-left px-3 py-2 text-sm hover:bg-gray-700 text-gray-200"
      @click="$emit('close')"
    >Close</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MapObject } from '@/types/api'

const props = defineProps<{
  object: MapObject
  x: number
  y: number
}>()

defineEmits<{ close: [] }>()

const displayName = computed(() => {
  if (props.object.host_name && props.object.service_description)
    return `${props.object.host_name} / ${props.object.service_description}`
  return props.object.host_name ?? props.object.group_name ?? props.object.id
})

function openInMonitoring() {
  // Placeholder: open Checkmk/Nagios link
  if (props.object.host_name) {
    window.open(`/nagios/cgi-bin/status.cgi?host=${props.object.host_name}`, '_blank')
  }
}
</script>
