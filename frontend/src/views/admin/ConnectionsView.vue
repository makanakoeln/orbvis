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
import { useCapabilitiesStore } from '@/stores/capabilities';
import ConnectionsFormSpecView from '@/views/admin/ConnectionsFormSpecView.vue';
import ConnectionsViewLegacy from '@/views/admin/ConnectionsViewLegacy.vue';

const capabilities = useCapabilitiesStore();
</script>
