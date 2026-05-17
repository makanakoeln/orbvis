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
        :worldmap-view="worldmapView"
        @close="emit('close')"
        @updated="emit('updated')"
    />
    <BoardSettingsModalLegacy
        v-else
        :board="board"
        :worldmap-view="worldmapView"
        @close="emit('close')"
        @updated="emit('updated')"
    />
</template>

<script setup lang="ts">
import BoardSettingsFormSpecModal from '@/components/board/BoardSettingsFormSpecModal.vue';
import BoardSettingsModalLegacy from '@/components/board/BoardSettingsModalLegacy.vue';
import { useCapabilitiesStore } from '@/stores/capabilities';
import type { BoardRead } from '@/types/api';

defineProps<{
    board: BoardRead;
    worldmapView?: { lat: number; lng: number; zoom: number } | null;
}>();

const emit = defineEmits<{
    close: [];
    updated: [];
}>();

const capabilities = useCapabilitiesStore();
</script>
