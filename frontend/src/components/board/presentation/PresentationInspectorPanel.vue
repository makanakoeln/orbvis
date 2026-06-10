<template>
  <aside class="insp" @pointerdown.stop @dblclick.stop>
    <!-- Single selection: element properties -->
    <template v-if="single">
      <div class="insp__head">
        <input
          class="insp__name"
          :value="single.name ?? ''"
          :placeholder="kindTitle(single)"
          :title="_t('Element name')"
          @change="onRename"
        />
        <div class="insp__actions">
          <button class="insp__icon" :title="_t('Duplicate')" @click="emit('duplicate')">
            <span v-html="ICONS.duplicate" />
          </button>
          <button
            class="insp__icon insp__icon--danger"
            :title="_t('Delete')"
            @click="emit('delete')"
          >
            <span v-html="ICONS.trash" />
          </button>
        </div>
      </div>
      <CmkScrollContainer class="insp__body-wrap">
        <div class="insp__body">
          <div v-if="single.kind === 'group'" class="insp__hint">
            {{ _t('Group — move or duplicate it as one unit. Ungroup via the layers panel.') }}
          </div>
          <InspectorLayoutSection
            v-if="showLayout"
            :element="single"
            @patch="emit('patch', $event)"
          />
          <InspectorTypographySection
            v-if="single.kind === 'text'"
            :element="single"
            @patch="emit('patch', $event)"
          />
          <InspectorAppearanceSection
            v-if="single.kind === 'shape'"
            :element="single"
            @patch="emit('patch', $event)"
          />
          <InspectorImageSection
            v-if="single.kind === 'image'"
            :element="single"
            @patch="emit('patch', $event)"
          />
          <InspectorDataSection
            v-if="single.kind === 'data' || single.kind === 'shape'"
            :element="single"
            :connection-id="connectionId"
            :targets="targets"
            @patch="emit('patch', $event)"
          />
        </div>
      </CmkScrollContainer>
    </template>

    <!-- Multi selection -->
    <template v-else-if="selection.length > 1">
      <div class="insp__head">
        <span class="insp__title">{{
          _t('%{n} elements selected', { n: String(selection.length) })
        }}</span>
        <div class="insp__actions">
          <button class="insp__icon" :title="_t('Duplicate')" @click="emit('duplicate')">
            <span v-html="ICONS.duplicate" />
          </button>
          <button
            class="insp__icon insp__icon--danger"
            :title="_t('Delete')"
            @click="emit('delete')"
          >
            <span v-html="ICONS.trash" />
          </button>
        </div>
      </div>
      <div class="insp__body">
        <div class="insp__row">
          <span class="orb-cap">{{ _t('Opacity') }}</span>
          <input
            class="orb-range"
            type="range"
            min="0"
            max="100"
            :value="Math.round(multiOpacity * 100)"
            @input="onMultiOpacity"
          />
          <span class="orb-range-pct">{{ Math.round(multiOpacity * 100) }}%</span>
        </div>
        <div class="insp__hint">
          {{ _t('Use the toolbar above the slide to align and distribute.') }}
        </div>
      </div>
    </template>

    <!-- No selection: slide settings -->
    <template v-else>
      <div class="insp__head">
        <span class="insp__title">{{ _t('Slide') }}</span>
      </div>
      <CmkScrollContainer class="insp__body-wrap">
        <div class="insp__body">
          <section class="insp__section">
            <h3 class="orb-section-title">{{ _t('Theme') }}</h3>
            <CmkDropdown
              :selected-option="view.theme"
              :options="themeDropdownOptions"
              :width="'fill'"
              :label="_t('Theme')"
              @update:selected-option="emit('slide', { theme: $event as PresentationTheme })"
            />
          </section>
          <section class="insp__section">
            <h3 class="orb-section-title">{{ _t('Aspect / size') }}</h3>
            <div class="insp__presets">
              <button
                v-for="p in slidePresets"
                :key="p.label"
                class="insp__preset"
                :class="{ 'insp__preset--on': view.width === p.w && view.height === p.h }"
                @click="emit('slide', { width: p.w, height: p.h })"
              >
                {{ p.label }}
              </button>
            </div>
            <div class="insp__row">
              <label class="insp__num">
                <span class="orb-cap">{{ _t('Width') }}</span>
                <NumberInput
                  :model-value="view.width"
                  min="320"
                  max="8192"
                  @update:model-value="$event !== null && emit('slide', { width: $event })"
                />
              </label>
              <label class="insp__num">
                <span class="orb-cap">{{ _t('Height') }}</span>
                <NumberInput
                  :model-value="view.height"
                  min="320"
                  max="8192"
                  @update:model-value="$event !== null && emit('slide', { height: $event })"
                />
              </label>
            </div>
          </section>
          <section class="insp__section">
            <h3 class="orb-section-title">{{ _t('Background') }}</h3>
            <div class="insp__row">
              <ColorField
                :label="_t('Background color')"
                :value="view.background ?? null"
                @set="emit('slide', { background: $event })"
              />
              <span class="insp__hint insp__hint--inline">{{
                view.background ? view.background : _t('Theme default')
              }}</span>
            </div>
            <ImagePicker
              :model-value="backgroundImageName"
              :placeholder="_t('Background image…')"
              @update:model-value="emit('slide', { background_image: $event || null })"
            />
          </section>
          <section v-if="$slots.slide" class="insp__section">
            <slot name="slide" />
          </section>
        </div>
      </CmkScrollContainer>
    </template>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import NumberInput from '@/components/NumberInput.vue'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkScrollContainer from '@/components/cmk/CmkScrollContainer'

import type { PresentationElement, PresentationTheme, PresentationView } from '@/types/api'
import { ICONS, SLIDE_PRESETS } from '@/utils/presentationCanvasChrome'
import { themeOptions } from '@/utils/presentationThemes'
import usei18n from '@/vendor/cmk/lib/i18n'

import ImagePicker from '../ImagePicker.vue'
import ColorField from './ColorField.vue'
import InspectorAppearanceSection from './inspector/InspectorAppearanceSection.vue'
import InspectorDataSection from './inspector/InspectorDataSection.vue'
import InspectorImageSection from './inspector/InspectorImageSection.vue'
import InspectorLayoutSection from './inspector/InspectorLayoutSection.vue'
import InspectorTypographySection from './inspector/InspectorTypographySection.vue'

const { _t } = usei18n()

const props = defineProps<{
  selection: PresentationElement[]
  view: PresentationView
  connectionId: string
  targets: { id: string; name: string }[]
  backgroundImageName: string
}>()

const emit = defineEmits<{
  patch: [Record<string, unknown>]
  delete: []
  duplicate: []
  slide: [Partial<PresentationView>]
}>()

const single = computed(() => (props.selection.length === 1 ? props.selection[0] : undefined))

// A connector's x/y/w/h is vestigial (its endpoints drive the geometry), and a
// group's box doesn't move its children — neither gets the Layout numbers.
const showLayout = computed(() => {
  const el = single.value
  if (!el || el.kind === 'group') return false
  return !(el.kind === 'shape' && (el.shape === 'line' || el.shape === 'arrow'))
})

function kindTitle(el: PresentationElement): string {
  if (el.kind === 'text') return _t('Text')
  if (el.kind === 'image') return _t('Image')
  if (el.kind === 'data') return _t('Live status')
  if (el.kind === 'group') return _t('Group')
  return el.shape.charAt(0).toUpperCase() + el.shape.slice(1)
}

function onRename(e: Event): void {
  const name = (e.target as HTMLInputElement).value.trim()
  emit('patch', { name: name || null })
}

const multiOpacity = computed(() => {
  if (!props.selection.length) return 1
  return Math.max(...props.selection.map((e) => e.opacity))
})
function onMultiOpacity(e: Event): void {
  emit('patch', { opacity: Number((e.target as HTMLInputElement).value) / 100 })
}

const themeDropdownOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: themeOptions().map((t) => ({ name: t.name, title: t.title }))
}))

const slidePresets = SLIDE_PRESETS
</script>

<style scoped>
.insp {
  display: flex;
  flex-direction: column;
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-surface, #1b1f2a);
  border-left: 1px solid var(--border, rgb(255 255 255 / 8%));
  color: var(--text, #e5e7eb);
  z-index: 5;
}

.insp__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border, rgb(255 255 255 / 8%));
  min-height: 44px;
  box-sizing: border-box;
}

.insp__title {
  font-weight: 600;
  font-size: var(--font-size-large);
}

.insp__name {
  flex: 1;
  min-width: 0;
  padding: 4px 6px;
  font-weight: 600;
  font-size: var(--font-size-large);
  color: var(--text);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
}

.insp__name:hover {
  border-color: var(--default-form-element-border-color);
}

.insp__name:focus {
  outline: none;
  border-color: var(--color-corporate-green-50);
  background: var(--default-form-element-bg-color);
}

.insp__actions {
  display: flex;
  gap: 2px;
}

.insp__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.insp__icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.insp__icon:hover {
  background: var(--bg-hover, rgb(255 255 255 / 8%));
  color: var(--text);
}

.insp__icon--danger:hover {
  background: color-mix(in srgb, var(--color-red-50, #e9546b) 20%, transparent);
}

.insp__body-wrap {
  flex: 1;
  min-height: 0;
}

.insp__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 12px;
}

.insp__section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insp__row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.insp__num {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.insp__presets {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.insp__preset {
  padding: 6px 4px;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: var(--font-size-normal);
}

.insp__preset:hover {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.insp__preset--on {
  border-color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 18%, transparent);
}

.insp__hint {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
  line-height: 1.4;
}

.insp__hint--inline {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
