<!--
OrbVis stub for cmk-frontend-vue/src/form/FormReadonly.vue.

The full upstream component pulls in a deep tree of render helpers
(FormConditionChoices, FormLabelsLabel, CmkTimeSpan, CmkDualList,
FormCheckboxListChoice, FormFileUpload, …) that the OrbVis Pilot
vocabulary doesn't ship. The Pilot only runs in
``display_mode="edit"``, so the readonly branch is never reached at
runtime. Restore the upstream version (and the missing dependencies)
when readonly rendering is actually needed.

Wired up via ``CMK_STUBS`` in ``frontend/vite.config.ts`` so the
vendored file at ``vendor/cmk/form/FormReadonly.vue`` no longer needs
a patch on disk.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components';

defineProps<{
    spec: FormSpec;
    data: unknown;
    backendValidation: unknown;
}>();
</script>

<template>
    <pre>{{ JSON.stringify(data, null, 2) }}</pre>
</template>
