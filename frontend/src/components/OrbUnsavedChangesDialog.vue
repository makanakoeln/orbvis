<template>
  <CmkPopupDialog :open="open" icon="warning" :title="title" @close="$emit('cancel')">
    <CmkParagraph class="orb-unsaved__message">{{ message }}</CmkParagraph>
    <div class="orb-unsaved__actions">
      <CmkButton ref="stayBtnRef" variant="optional" @click="$emit('cancel')">
        {{ stayLabel }}
      </CmkButton>
      <CmkButton variant="secondary" @click="$emit('confirm')">
        {{ discardLabel }}
      </CmkButton>
    </div>
  </CmkPopupDialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import CmkButton from '@/components/cmk/CmkButton'
import CmkPopupDialog from '@/components/cmk/CmkPopupDialog'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'

import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{ open: boolean }>()
defineEmits<{ confirm: []; cancel: [] }>()

const title = computed(() => _t('Discard unsaved changes?'))
const message = computed(() =>
  _t('You have unsaved changes on this page. Leaving now will discard them.')
)
const discardLabel = computed(() => _t('Discard changes'))
const stayLabel = computed(() => _t('Stay on page'))

// Pre-select the safe action so Enter dismisses the dialog instead of
// destroying work. CmkPopup disables reka-ui's auto-focus, so the focus
// must be set explicitly after the portal has rendered.
const stayBtnRef = ref<{ $el: HTMLElement } | null>(null)

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    // CmkPopup focuses its own DialogContent in a `nextTick` after the
    // portal mounts. Wait two ticks so our explicit focus overrides it.
    await nextTick()
    await nextTick()
    stayBtnRef.value?.$el?.focus()
  }
)
</script>

<style scoped>
.orb-unsaved__message {
  margin-bottom: var(--dimension-6);
}

.orb-unsaved__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-3);
}
</style>

<style>
/* Der Dialog kommt aus einem Slide-In (z-index-modal). Beide Container teilen
   sich dieselbe Stack-Ebene; wenn das Slide-In nach dem Schließen-Versuch
   neu geöffnet wird (z. B. Map-View-Picker), landet es im DOM hinter dem
   gerade gemounteten Popup-Portal — der gleiche z-index reicht dann nicht.
   Ein expliziter Offset legt den Discard-Dialog garantiert obenauf. */
body:has(.cmk-slide-in__container) .cmk-popup__container,
body:has(.cmk-slide-in__container) .cmk-popup__overlay {
  z-index: calc(var(--z-index-modal) + 10);
}
</style>
