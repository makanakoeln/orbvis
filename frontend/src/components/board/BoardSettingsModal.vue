<!--
    Mode switch for the per-board Settings modal.

    Standalone (cmk.rulesets.v1 absent) renders the legacy plain-Vue
    modal that saves through ``boardsApi.update``; built-in / MKP keeps
    the FormSpec modal driven by ``/api/v1/boards/{name}/metadata`` +
    ``/-/metadata-schema``. Props/events are identical on both branches
    so the BoardView callsite stays unchanged.
-->
<template>
    <BoardSettingsFormSpecModal
        v-if="capabilities.formSpecs"
        :board="board"
        :worldmap-view="worldmapView ?? null"
        :parent-map-size="parentMapSize ?? null"
        @close="emit('close')"
        @updated="emit('updated')"
        @pick-worldmap-view="emit('pickWorldmapView', $event)"
        @worldmap-view-change="emit('worldmapViewChange', $event)"
    />
    <BoardSettingsModalLegacy
        v-else
        :board="board"
        :worldmap-view="worldmapView ?? null"
        @close="emit('close')"
        @updated="emit('updated')"
        @pick-worldmap-view="emit('pickWorldmapView', $event)"
        @worldmap-view-change="emit('worldmapViewChange', $event)"
    />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue';

import BoardSettingsModalLegacy from '@/components/board/BoardSettingsModalLegacy.vue';
import { useCapabilitiesStore } from '@/stores/capabilities';
import type { BoardRead } from '@/types/api';

const BoardSettingsFormSpecModal = defineAsyncComponent(
    () => import('@/components/board/BoardSettingsFormSpecModal.vue'),
);

defineProps<{
    board: BoardRead;
    worldmapView?: { lat: number; lng: number; zoom: number } | null;
    parentMapSize?: { width: number; height: number } | null;
}>();

const emit = defineEmits<{
    close: [];
    updated: [];
    pickWorldmapView: [done: (view: { lat: number; lng: number; zoom: number } | null) => void];
    worldmapViewChange: [view: { lat: number; lng: number; zoom: number }];
}>();

const capabilities = useCapabilitiesStore();
</script>
