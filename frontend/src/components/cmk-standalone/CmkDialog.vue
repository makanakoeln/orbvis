<!--
OrbVis-native CmkDialog, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. The upstream dismissal state is mirrored
into ``sessionStorage`` (instead of CMK's persistWarningDismissal REST
call) so the same prop surface continues to work — OrbVis standalone
has no Checkmk user-config endpoint.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import CmkButton from '@/components/cmk/CmkButton'

type Variant = 'error' | 'warning' | 'success' | 'info' | 'loading'

export interface CmkDialogProps {
  title?: string | undefined
  message: string
  buttons?: {
    title: string
    variant: 'primary' | 'secondary' | 'optional' | 'success' | 'warning' | 'danger' | 'info'
    onclick: () => void
  }[]
  dismissalButton?: { title: string; key: string }
  variant?: Variant
}

const props = withDefaults(defineProps<CmkDialogProps>(), { variant: 'info' })

const dialogHidden = ref(false)

function storageKey(key: string) {
  return `orbvis.dismiss:${key}`
}

function hideContent(event?: Event) {
  if (props.dismissalButton) {
    event?.stopPropagation()
    dialogHidden.value = true
    try {
      sessionStorage.setItem(storageKey(props.dismissalButton.key), '1')
    } catch {
      /* sessionStorage unavailable — silently skip */
    }
  }
}

const glyph = computed(() => {
  switch (props.variant) {
    case 'success':
      return '✓'
    case 'error':
    case 'warning':
      return '⚠'
    case 'loading':
      return '…'
    default:
      return 'ℹ'
  }
})

onMounted(() => {
  if (!props.dismissalButton) return
  try {
    if (sessionStorage.getItem(storageKey(props.dismissalButton.key)) === '1') {
      dialogHidden.value = true
    }
  } catch {
    /* sessionStorage unavailable */
  }
})
</script>

<template>
  <div v-if="!dialogHidden" class="orb-dialog">
    <div class="orb-dialog__icon" :class="`orb-dialog__icon--${variant}`" aria-hidden="true">
      {{ glyph }}
    </div>
    <div class="orb-dialog__content">
      <span v-if="title" class="orb-dialog__title">{{ title }}<br /></span>
      <span>{{ message }}</span>
      <div v-if="(buttons?.length ?? 0) > 0 || dismissalButton" class="orb-dialog__buttons">
        <CmkButton
          v-for="(button, idx) in buttons"
          :key="idx"
          :variant="button.variant"
          @click="button.onclick"
          >{{ button.title }}</CmkButton
        >
        <CmkButton v-if="dismissalButton" @click="hideContent($event)">
          {{ dismissalButton.title }}
        </CmkButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.orb-dialog {
  display: flex;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-surface, var(--ux-theme-3, #18181b));
  color: var(--font-color, #f4f4f5);
}

.orb-dialog__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  font-size: 18px;
  font-weight: 700;
  min-width: 32px;
}

.orb-dialog__icon--info {
  background-color: var(--color-mod-downtime, #3b82f6);
  color: white;
}

.orb-dialog__icon--error {
  background-color: var(--default-button-danger-color, #ef4444);
  color: white;
}

.orb-dialog__icon--warning {
  background-color: var(--color-warning, #ffd000);
  color: black;
}

.orb-dialog__icon--success {
  background-color: var(--color-corporate-green-50, #15d1a0);
  color: black;
}

.orb-dialog__icon--loading {
  background-color: var(--color-corporate-green-50, #15d1a0);
  color: black;
}

.orb-dialog__content {
  flex-grow: 1;
  padding: 10px;
  white-space: pre-line;
}

.orb-dialog__title {
  font-weight: 700;
  margin-bottom: 6px;
  display: block;
}

.orb-dialog__buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
</style>
