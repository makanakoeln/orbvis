<template>
  <OrbModal :open="true" :title="_t('Bundle into a location')" closable @close="$emit('close')">
    <form class="bundle-dialog__form" @submit.prevent="submit">
      <p class="bundle-dialog__intro">
        {{ _t('%{n} hosts will be merged into one worst-state location icon.', { n: hostCount }) }}
      </p>
      <div class="bundle-dialog__field">
        <label class="bundle-dialog__label">{{ _t('Name (optional)') }}</label>
        <CmkInput
          v-model="name"
          :placeholder="_t('e.g. Datacenter Zürich')"
          field-size="FILL"
          @keydown.enter.prevent="submit"
        />
      </div>
      <div class="bundle-dialog__field">
        <div class="bundle-dialog__type-grid" role="radiogroup" :aria-label="_t('Bundle type')">
          <button
            v-for="opt in typeCards"
            :key="opt.kind"
            type="button"
            role="radio"
            :aria-checked="kind === opt.kind"
            class="bundle-dialog__type-card"
            :class="{ 'bundle-dialog__type-card--selected': kind === opt.kind }"
            @click="kind = opt.kind"
          >
            <span class="bundle-dialog__type-card-title">{{ opt.title }}</span>
            <span class="bundle-dialog__type-card-desc">{{ opt.desc }}</span>
          </button>
        </div>
      </div>
    </form>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">{{ _t('Cancel') }}</CmkButton>
      <CmkButton variant="primary" @click="submit">{{ _t('Bundle') }}</CmkButton>
    </template>
  </OrbModal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import OrbModal from '@/components/OrbModal.vue'
import CmkButton from '@/components/cmk/CmkButton'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import usei18n from '@/vendor/cmk/lib/i18n'

type BundleKind = 'static' | 'location'

defineProps<{ hostCount: number }>()
const emit = defineEmits<{ close: []; confirm: [payload: { name: string; kind: BundleKind }] }>()

const { _t } = usei18n()

const name = ref('')
const kind = ref<BundleKind>('location')

const typeCards = computed<{ kind: BundleKind; title: string; desc: string }[]>(() => [
  {
    kind: 'location',
    title: _t('Location-bound'),
    desc: _t('Hosts at this coordinate — new hosts added there join automatically.')
  },
  {
    kind: 'static',
    title: _t('Fixed selection'),
    desc: _t('Exactly the selected hosts — does not change on its own.')
  }
])

function submit() {
  emit('confirm', { name: name.value.trim(), kind: kind.value })
}
</script>

<style scoped>
.bundle-dialog__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  min-width: 380px;
}

.bundle-dialog__intro {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}

.bundle-dialog__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.bundle-dialog__label {
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--text-muted);
}

.bundle-dialog__type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--dimension-3);
}

.bundle-dialog__type-card {
  text-align: left;
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition:
    border-color 120ms,
    background-color 120ms;
}

.bundle-dialog__type-card:hover {
  border-color: var(--color-corporate-green-50);
}

.bundle-dialog__type-card--selected {
  border-color: var(--color-corporate-green-50);
  background: color-mix(
    in srgb,
    var(--color-corporate-green-50) 10%,
    var(--default-form-element-bg-color)
  );
}

.bundle-dialog__type-card-title {
  font-size: var(--font-size-normal);
  font-weight: 600;
  color: var(--text);
}

.bundle-dialog__type-card-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.35;
}
</style>
