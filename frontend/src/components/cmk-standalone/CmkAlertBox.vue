<!--
OrbVis-native CmkAlertBox, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
Renders an inline alert with text-glyph icons (no CmkIcon dep), an
optional heading, and an optional close button. Auto-dismiss behaviour
matches upstream (6 s timeout).
-->
<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'

export type Variants = 'error' | 'warning' | 'success' | 'info' | 'loading'
export type Sizes = 'small' | 'medium'

export interface CmkAlertBoxProps {
  variant?: Variants
  size?: Sizes
  heading?: string | undefined
  autoDismiss?: boolean | undefined
  dismissible?: boolean | undefined
}

const props = withDefaults(defineProps<CmkAlertBoxProps>(), {
  variant: 'info',
  size: 'medium'
})

const open = defineModel<boolean>('open', { default: true })

let timeoutId: number | null = null
watch(
  [open, () => props.autoDismiss],
  ([newOpen]) => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    if (newOpen && props.autoDismiss) {
      timeoutId = window.setTimeout(() => {
        open.value = false
      }, 6000)
    }
  },
  { immediate: true }
)
onUnmounted(() => {
  if (timeoutId !== null) clearTimeout(timeoutId)
})

const glyph = computed(() => {
  switch (props.variant) {
    case 'error':
      return '⚠'
    case 'warning':
      return '⚠'
    case 'success':
      return '✓'
    case 'loading':
      return '…'
    default:
      return 'ℹ'
  }
})
</script>

<template>
  <div
    v-if="open"
    class="orb-alert"
    :class="[`orb-alert--${variant}`, `orb-alert--size-${size}`]"
    :role="variant === 'error' || variant === 'warning' ? 'alert' : 'status'"
  >
    <div class="orb-alert__icon" aria-hidden="true">{{ glyph }}</div>
    <div class="orb-alert__text">
      <h4 v-if="$slots.heading || heading" class="orb-alert__heading">
        <slot name="heading">{{ heading }}</slot>
      </h4>
      <div class="orb-alert__body"><slot /></div>
    </div>
    <button
      v-if="dismissible"
      type="button"
      class="orb-alert__close"
      aria-label="Close"
      @click="open = false"
    >
      ×
    </button>
  </div>
</template>

<style scoped>
.orb-alert {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 4px;
  margin: 12px 0;
  gap: 12px;
  color: var(--font-color, #f4f4f5);
}

.orb-alert__icon {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
}

.orb-alert__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  flex: 1;
}

.orb-alert__heading {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
}

.orb-alert__close {
  flex-shrink: 0;
  background: none;
  border: none;
  padding: 0;
  color: inherit;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.orb-alert--error {
  background: color-mix(in srgb, var(--default-button-danger-color, #ef4444) 30%, transparent);
}

.orb-alert--warning {
  background: color-mix(in srgb, var(--color-warning, #ffd000) 25%, transparent);
}

.orb-alert--success {
  background: color-mix(in srgb, var(--color-corporate-green-50, #15d1a0) 25%, transparent);
}

.orb-alert--info,
.orb-alert--loading {
  background: color-mix(in srgb, var(--color-mod-downtime, #3b82f6) 25%, transparent);
}

.orb-alert--size-small {
  padding: 4px 12px;
}

.orb-alert--size-small .orb-alert__icon {
  width: 14px;
  font-size: 12px;
}
</style>
