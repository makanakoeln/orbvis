<template>
  <div class="ptg" @pointerdown.stop>
    <div class="ptg__card">
      <div class="ptg__head">
        <div>
          <h2 class="ptg__title">{{ _t('Start with a design') }}</h2>
          <p class="ptg__sub">
            {{ _t('Pick a template, then connect your hosts and services — or start blank.') }}
          </p>
        </div>
        <button class="ptg__x" :title="_t('Close')" @click="emit('close')">×</button>
      </div>
      <CmkScrollContainer class="ptg__grid-wrap">
        <div class="ptg__grid">
          <button v-for="t in templates" :key="t.id" class="ptg__item" @click="emit('apply', t)">
            <PresentationSlidePreview
              v-if="t.id !== 'blank'"
              :elements="previewElements(t)"
              :theme="t.theme"
            />
            <div v-else class="ptg__blank">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </div>
            <span class="ptg__item-title">{{ t.title }}</span>
            <span class="ptg__item-desc">{{ t.description }}</span>
          </button>
        </div>
      </CmkScrollContainer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import CmkScrollContainer from '@/components/cmk/CmkScrollContainer'

import type { PresentationElement } from '@/types/api'
import { type PresentationTemplate, presentationTemplates } from '@/utils/presentationTemplates'
import usei18n from '@/vendor/cmk/lib/i18n'

import PresentationSlidePreview from './PresentationSlidePreview.vue'

const { _t } = usei18n()

const emit = defineEmits<{ apply: [PresentationTemplate]; close: [] }>()

const templates = computed(() => presentationTemplates(_t))

// Build once per gallery open — element ids are freshly generated per build,
// so the preview must not rebuild on every render.
const previewCache = new Map<string, PresentationElement[]>()
function previewElements(t: PresentationTemplate): PresentationElement[] {
  let els = previewCache.get(t.id)
  if (!els) {
    els = t.build()
    previewCache.set(t.id, els)
  }
  return els
}
</script>

<style scoped>
.ptg {
  position: absolute;
  inset: 0;
  z-index: 8;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 45%);
}

.ptg__card {
  display: flex;
  flex-direction: column;
  width: min(920px, calc(100% - 64px));
  max-height: calc(100% - 64px);
  border-radius: 14px;
  background: var(--bg-surface, #1b1f2a);
  border: 1px solid var(--border, rgb(255 255 255 / 8%));
  box-shadow: 0 24px 64px rgb(0 0 0 / 50%);
  color: var(--text, #e5e7eb);
}

.ptg__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 24px 12px;
}

.ptg__title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.ptg__sub {
  margin: 4px 0 0;
  font-size: var(--font-size-large);
  color: var(--text-muted);
}

.ptg__x {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 22px;
  cursor: pointer;
}

.ptg__x:hover {
  color: var(--text);
}

.ptg__grid-wrap {
  flex: 1;
  min-height: 0;
}

.ptg__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(264px, 1fr));
  gap: 16px;
  padding: 12px 24px 24px;
}

.ptg__item {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
  padding: 8px;
  border: 1px solid var(--border, rgb(255 255 255 / 10%));
  border-radius: 12px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.12s ease,
    transform 0.12s ease;
}

.ptg__item:hover {
  border-color: var(--color-corporate-green-50);
  transform: translateY(-2px);
}

.ptg__blank {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 139px;
  border: 1px dashed var(--border, rgb(255 255 255 / 18%));
  border-radius: 8px;
  color: var(--text-muted);
}

.ptg__blank svg {
  width: 36px;
  height: 36px;
}

.ptg__item-title {
  margin-top: 6px;
  font-weight: 600;
  font-size: var(--font-size-large);
}

.ptg__item-desc {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}
</style>
