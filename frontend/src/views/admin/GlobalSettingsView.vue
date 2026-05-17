<!--
    Mode switch for the Global Settings admin surface.

    Built-in / MKP deployments expose the FormSpec view backed by
    ``GET /api/v1/settings/schema`` + ``/form``. The Standalone (Docker)
    build ships without cmk.rulesets.v1 — those endpoints aren't
    registered, so the capabilities store reports ``form_specs: false``
    and we render the legacy plain-Vue form over the flat pydantic
    ``GET/PUT /api/v1/settings`` endpoints instead.
-->
<template>
    <GlobalSettingsFormSpecView v-if="capabilities.formSpecs" />
    <GlobalSettingsViewLegacy v-else />
</template>

<script setup lang="ts">
import { useCapabilitiesStore } from '@/stores/capabilities';
import GlobalSettingsFormSpecView from '@/views/admin/GlobalSettingsFormSpecView.vue';
import GlobalSettingsViewLegacy from '@/views/admin/GlobalSettingsViewLegacy.vue';

const capabilities = useCapabilitiesStore();
</script>
