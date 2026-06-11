<template>
  <OrbModal :open="true" closable @close="$emit('close')">
    <template #header>
      <span class="changelog-modal__title">
        Changelog
        <span class="changelog-modal__version">OrbVis v{{ appVersion }}</span>
      </span>
    </template>

    <div class="changelog-modal__content">
      <div v-if="loading" class="changelog-modal__loading">Loading…</div>
      <div v-else-if="error" class="changelog-modal__error">{{ error }}</div>
      <pre v-else class="changelog-modal__text">{{ content }}</pre>
    </div>

    <template #footer>
      <CmkButton variant="primary" @click="$emit('close')">{{ _t('Got it') }}</CmkButton>
    </template>
  </OrbModal>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import OrbModal from '@/components/OrbModal.vue'
import CmkButton from '@/components/cmk/CmkButton'

import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()

defineEmits<{ close: [] }>()

const appVersion = __APP_VERSION__
const content = ref('')
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}api/changelog`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    content.value = await res.text()
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.changelog-modal__title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.changelog-modal__version {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  color: var(--text-muted);
}

.changelog-modal__content {
  width: min(640px, 90vw);
  max-height: 60vh;
  overflow-y: auto;
}

.changelog-modal__loading {
  padding: var(--dimension-9) 0;
  text-align: center;
  font-size: var(--font-size-large);
  color: var(--text-muted);
}

.changelog-modal__error {
  font-size: var(--font-size-large);
  color: var(--color-light-red-40);
}

.changelog-modal__text {
  font-size: var(--font-size-normal);
  color: var(--text);
  font-family: monospace;
  white-space: pre-wrap;
  line-height: 1.6;
  margin: 0;
}
</style>
