<!--
OrbVis override for cmk-frontend-vue/src/form/private/forms/FormMultilineText.vue.

Upstream renders a bare <textarea> that picks up no theme background or
border — in dark mode it ends up as a near-invisible black rectangle on
a near-black surface. This override duplicates the upstream template
and adds the OrbVis theme styles in a scoped block so the styling never
leaks into other textareas (e.g. the textbox-map widget).
Registered through ``orbFormComponents``; the vendored upstream file
stays byte-identical.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

defineProps<{
  spec: FormSpec.MultilineText
  backendValidation: unknown
}>()

const value = defineModel<string>('data', { required: true })
</script>

<template>
  <div class="form-multiline-text">
    <label v-if="spec.label" class="form-multiline-text__label">{{ spec.label }}</label>
    <textarea
      v-model="value"
      :placeholder="spec.input_hint || ''"
      :aria-label="spec.label || spec.title"
      class="form-multiline-text__textarea"
      :class="{ 'form-multiline-text__textarea--monospace': spec.monospaced }"
      rows="4"
    />
  </div>
</template>

<style scoped>
.form-multiline-text {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3, 4px);
}

.form-multiline-text__label {
  color: var(--text);
  font-size: var(--font-size-normal);
}

.form-multiline-text__textarea {
  width: 432px;
  max-width: 100%;
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

.form-multiline-text__textarea--monospace {
  font-family: monospace, sans-serif;
}

.form-multiline-text__textarea:focus {
  outline: none;
  border-color: var(--color-corporate-green-50, #15d1a0);
}

.form-multiline-text__textarea::placeholder {
  color: var(--text-muted, #9ca3af);
  opacity: 0.6;
}
</style>
