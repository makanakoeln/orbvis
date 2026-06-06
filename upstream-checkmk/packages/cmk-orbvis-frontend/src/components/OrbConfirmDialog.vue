<template>
  <CmkPopup :open="open" @close="$emit('cancel')">
    <div class="orb-confirm-dialog">
      <CmkDialog
        v-if="open"
        :variant="variant"
        :title="title"
        :message="message"
        :buttons="dialogButtons"
      />
    </div>
  </CmkPopup>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import CmkDialog from '@/components/cmk/CmkDialog'
import CmkPopup from '@/components/cmk/CmkPopup'

import usei18n from '@cmk/lib/i18n'

type DialogVariant = 'error' | 'warning' | 'success' | 'info'
type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'optional'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    message?: string
    confirmLabel?: string
    cancelLabel?: string
    confirmVariant?: ButtonVariant
    variant?: DialogVariant
  }>(),
  {
    message: '',
    confirmLabel: '',
    cancelLabel: '',
    confirmVariant: 'warning',
    variant: 'warning'
  }
)

const emit = defineEmits<{ confirm: []; cancel: [] }>()
const { _t } = usei18n()

const dialogButtons = computed(() => [
  {
    title: props.confirmLabel || _t('Confirm'),
    variant: props.confirmVariant,
    onclick: () => emit('confirm')
  },
  {
    title: props.cancelLabel || _t('Cancel'),
    variant: 'secondary' as ButtonVariant,
    onclick: () => emit('cancel')
  }
])
</script>

<style scoped>
.orb-confirm-dialog {
  width: 420px;
  max-width: 90vw;
}

/* !important: CmkDialog scoped CSS hat höhere Specificity als :deep(). */
.orb-confirm-dialog :deep(.cmk-dialog__content) {
  padding: var(--dimension-7) var(--dimension-8) !important;
  line-height: 1.45;
}

.orb-confirm-dialog :deep(.cmk-dialog__title) {
  font-size: var(--font-size-large) !important;
  margin-bottom: var(--dimension-2) !important;
  line-height: 1.4 !important;
}

.orb-confirm-dialog :deep(.cmk-dialog__icon-box) {
  padding: 0 var(--dimension-5) !important;
  align-self: stretch;
  justify-content: center;
}

.orb-confirm-dialog :deep(.cmk-dialog__icon) {
  padding: var(--dimension-1) !important;
}

.orb-confirm-dialog :deep(.buttons) {
  margin-top: var(--dimension-6) !important;
  display: flex;
  align-items: center;
}
</style>
