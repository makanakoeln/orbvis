<!--
    Mode switch for the System Settings admin surface — see
    GlobalSettingsView for the rationale. Standalone renders the legacy
    plain-Vue form (log_level + checkmk_url) over the flat
    ``GET/PUT /api/v1/settings/system`` endpoints; built-in / MKP keeps
    the FormSpec view.
-->
<template>
    <SystemSettingsFormSpecView v-if="capabilities.formSpecs" />
    <SystemSettingsViewLegacy v-else />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue';

import { useCapabilitiesStore } from '@/stores/capabilities';
import SystemSettingsViewLegacy from '@/views/admin/SystemSettingsViewLegacy.vue';

const SystemSettingsFormSpecView = defineAsyncComponent(
    () => import('@/views/admin/SystemSettingsFormSpecView.vue'),
);

const capabilities = useCapabilitiesStore();
</script>
