<!--
OrbVis override for the upstream
cmk-frontend-vue/src/form/private/forms/FormBooleanChoice.vue.

BooleanChoice in OrbVis is always a *state* toggle (Visibility, Use
color, Verify SSL, …), never a CMK-style accept/confirm checkbox.
CmkSwitch reads as a state more clearly, so we render the same data
with the slider instead. Registered through ``orbFormComponents`` so
the vendored upstream file stays byte-identical.
-->
<script setup lang="ts">
import type { BooleanChoice } from 'cmk-shared-typing/typescript/vue_formspec_components';

import CmkSwitch from '@/components/cmk/CmkSwitch';

defineProps<{
    spec: BooleanChoice;
    backendValidation: unknown;
}>();

const value = defineModel<boolean>('data', { required: true });
</script>

<template>
    <label class="form-boolean-choice">
        <CmkSwitch v-model:data="value" />
        <span v-if="spec.label" class="form-boolean-choice__label">{{ spec.label }}</span>
    </label>
</template>

<style scoped>
.form-boolean-choice {
    display: inline-flex;
    align-items: center;
    gap: var(--dimension-3, 8px);
    cursor: pointer;
}

.form-boolean-choice__label {
    color: var(--text);
    font-size: var(--font-size-normal);
}
</style>
