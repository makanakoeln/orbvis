<!--
    Mode switch for the Connections admin surface — see GlobalSettingsView
    for the rationale. Standalone renders the legacy plain-Vue modal-based
    CRUD form over the flat ``/api/v1/connections`` endpoints; built-in /
    MKP keeps the FormSpec / CascadingSingleChoice editor.
-->
<template>
    <ConnectionsFormSpecView v-if="capabilities.formSpecs" />
    <ConnectionsViewLegacy v-else />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue';

import { useCapabilitiesStore } from '@/stores/capabilities';
import ConnectionsViewLegacy from '@/views/admin/ConnectionsViewLegacy.vue';

// FormSpec view loads lazily so the vendored cmk-frontend-vue form
// stack lands in a separate chunk — the standalone build never fetches
// it because capabilities.formSpecs stays false.
const ConnectionsFormSpecView = defineAsyncComponent(
    () => import('@/views/admin/ConnectionsFormSpecView.vue'),
);

const capabilities = useCapabilitiesStore();
</script>
