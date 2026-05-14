<!--
OrbVis stub. The full upstream FormReadonly imports a deep tree of
render helpers (FormConditionChoices, FormLabelsLabel, CmkTimeSpan
utilities, …) that aren't part of the OrbVis Pilot vocabulary. The
Pilot only runs in display_mode="edit", so the readonly branch is
never reached at runtime. Restore the upstream version when readonly
rendering is actually needed.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components';

import type { ValidationMessages } from '@/form/private/validation';

defineProps<{
    spec: FormSpec;
    data: unknown;
    backendValidation: ValidationMessages;
}>();
</script>

<template>
    <pre>{{ JSON.stringify(data, null, 2) }}</pre>
</template>
