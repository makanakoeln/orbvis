<template>
  <label class="cf" :title="title">
    <!-- When unset the swatch previews the effective theme colour with a dashed
         border ("inherited"); the picker opens on that colour too. A theme whose
         default is transparent (e.g. text background) shows a checkerboard. -->
    <span
      class="cf__swatch"
      :class="{ 'cf__swatch--auto': !value, 'cf__swatch--empty': showsCheckerboard }"
      :style="swatchStyle"
    >
      <input type="color" class="cf__input" :value="pickerValue" @input="onInput" />
    </span>
    <!-- Clearing to null returns the element to the theme default. -->
    <button
      v-if="value"
      class="cf__clear"
      :title="_t('Use theme color')"
      @click.prevent="emit('set', null)"
    >
      ×
    </button>
  </label>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  label: string
  value: string | null | undefined
  /** Effective colour applied when no explicit value is set. Resolved from the
      active presentation theme; omit (or pass 'transparent') for properties
      that default to no colour. */
  defaultColor?: string
}>()
const emit = defineEmits<{ set: [string | null] }>()

const HEX_RE = /^#[0-9a-fA-F]{6}$/

const effective = computed(() => props.value || props.defaultColor || '')
const showsCheckerboard = computed(
  () => !props.value && (!props.defaultColor || props.defaultColor === 'transparent')
)
const swatchStyle = computed(() =>
  showsCheckerboard.value ? undefined : { backgroundColor: effective.value }
)
const pickerValue = computed(() => (HEX_RE.test(effective.value) ? effective.value : '#3b82f6'))
const title = computed(() =>
  props.value ? `${props.label}: ${props.value}` : `${props.label}: ${_t('theme default')}`
)

function onInput(e: Event): void {
  emit('set', (e.target as HTMLInputElement).value)
}
</script>

<style scoped>
.cf {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.cf__swatch {
  position: relative;
  width: 28px;
  height: 28px;
  border-radius: 5px;
  border: 1px solid var(--border, rgb(255 255 255 / 20%));
  overflow: hidden;
  cursor: pointer;
}

/* Unset: the colour is inherited from the theme — dashed border signals "auto". */
.cf__swatch--auto {
  border-style: dashed;
  border-color: var(--text-muted, #8b93a7);
}

/* Transparent default: standard checkerboard so "no colour" reads clearly. */
.cf__swatch--empty {
  background-image:
    linear-gradient(45deg, rgb(255 255 255 / 12%) 25%, transparent 25%),
    linear-gradient(-45deg, rgb(255 255 255 / 12%) 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, rgb(255 255 255 / 12%) 75%),
    linear-gradient(-45deg, transparent 75%, rgb(255 255 255 / 12%) 75%);
  background-size: 10px 10px;
  background-position:
    0 0,
    0 5px,
    5px -5px,
    -5px 0;
}

.cf__input {
  position: absolute;
  inset: -4px;
  width: 40px;
  height: 40px;
  border: none;
  padding: 0;
  cursor: pointer;
  opacity: 0;
}

.cf__clear {
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  color: var(--text-muted, #8b93a7);
  cursor: pointer;
  line-height: 1;
}
</style>
