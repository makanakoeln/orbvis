<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.

Vendored from cmk-frontend-vue/src/form/private/forms/FormMultilineText.vue.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components';
import { computed } from 'vue';

import FormValidation from '@/components/user-input/CmkInlineValidation.vue';
import { inputSizes } from '@/components/user-input/sizes';
import FormLabel from '@/form/private/FormLabel.vue';
import { useValidation, type ValidationMessages } from '@/form/private/validation';

const props = defineProps<{
    spec: FormSpec.MultilineText;
    backendValidation: ValidationMessages;
}>();

const data = defineModel<string>('data', { required: true });
const [validation, value] = useValidation<string>(
    data,
    props.spec.validators,
    () => props.backendValidation,
);

const style = computed(() => {
    return {
        ...(props.spec.monospaced ? { 'font-family': 'monospace, sans-serif' } : {}),
        width: inputSizes['LARGE'].width,
    };
});
</script>

<template>
    <div>
        <div v-if="spec.label">
            <FormLabel>{{ spec.label }}</FormLabel
            ><br />
        </div>
        <FormValidation :validation="validation"></FormValidation>
        <textarea
            v-model="value"
            :style="style"
            :placeholder="spec.input_hint || ''"
            :aria-label="spec.label || spec.title"
            :class="{ 'form-multiline-text__validation-error': validation.length > 0 }"
            rows="4"
        />
    </div>
</template>

<style scoped>
/* OrbVis additions on top of the upstream vendored file: the raw
   <textarea> picks up no theme background / border, so in dark mode it
   ends up as a near-invisible black rectangle on a near-black surface.
   These rules pull the same theme vars CmkInput uses so the textarea
   matches single-line inputs visually. */
textarea {
    background: var(--default-form-element-bg-color, var(--ux-theme-0, #1f2937));
    color: var(--font-color, #e5e7eb);
    border: 1px solid var(--default-form-element-border-color, var(--ux-theme-3, #4b5563));
    border-radius: 4px;
    padding: 6px 8px;
    font-family: inherit;
    font-size: 13px;
    resize: vertical;
    min-height: 80px;
}

textarea:focus {
    outline: none;
    border-color: var(--color-corporate-green-50, #15d1a0);
}

textarea::placeholder {
    color: var(--text-muted, #9ca3af);
    opacity: 0.6;
}

.form-multiline-text__validation-error {
    border-color: var(--inline-error-border-color, #ef4444);
}
</style>
