<template>
  <label class="cf" :title="label">
    <!-- backgroundColor (not the ``background`` shorthand) so the cf__swatch--auto
         "no colour" diagonal stays visible instead of being reset to none. -->
    <span
      class="cf__swatch"
      :style="{ backgroundColor: value || 'transparent' }"
      :class="{ 'cf__swatch--auto': !value }"
    >
      <input type="color" class="cf__input" :value="value || '#3b82f6'" @input="onInput" />
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
import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()

defineProps<{ label: string; value: string | null | undefined }>()
const emit = defineEmits<{ set: [string | null] }>()

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

.cf__swatch--auto {
  background-image: linear-gradient(45deg, transparent 45%, #f472b6 45% 55%, transparent 55%);
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
