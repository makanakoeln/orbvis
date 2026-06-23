<!--
    Mode switch for the per-map Settings modal.

    Standalone (cmk.rulesets.v1 absent) renders the legacy plain-Vue
    modal that saves through ``mapsApi.update``; built-in / MKP keeps
    the FormSpec modal driven by ``/api/v1/maps/{name}/metadata`` +
    ``/-/metadata-schema``. Props/events are identical on both branches
    so the MapView callsite stays unchanged.
-->
<template>
  <MapSettingsFormSpecModal
    v-if="capabilities.formSpecs"
    :map="map"
    :worldmap-view="worldmapView ?? null"
    :parent-map-size="parentMapSize ?? null"
    @close="emit('close')"
    @updated="emit('updated')"
    @pick-worldmap-view="emit('pickWorldmapView', $event)"
    @worldmap-view-change="emit('worldmapViewChange', $event)"
  />
  <MapSettingsModalLegacy
    v-else
    :map="map"
    :worldmap-view="worldmapView ?? null"
    @close="emit('close')"
    @updated="emit('updated')"
    @pick-worldmap-view="emit('pickWorldmapView', $event)"
    @worldmap-view-change="emit('worldmapViewChange', $event)"
  />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

import MapSettingsModalLegacy from '@/components/map/MapSettingsModalLegacy.vue'

import { useCapabilitiesStore } from '@/stores/capabilities'
import type { MapRead } from '@/types/api'

const MapSettingsFormSpecModal = defineAsyncComponent(
  () => import('@/components/map/MapSettingsFormSpecModal.vue')
)

defineProps<{
  map: MapRead
  worldmapView?: { lat: number; lng: number; zoom: number } | null
  parentMapSize?: { width: number; height: number } | null
}>()

const emit = defineEmits<{
  close: []
  updated: []
  pickWorldmapView: [done: (view: { lat: number; lng: number; zoom: number } | null) => void]
  worldmapViewChange: [view: { lat: number; lng: number; zoom: number }]
}>()

const capabilities = useCapabilitiesStore()
</script>
