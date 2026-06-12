<template>
  <section class="ins">
    <h3 class="orb-section-title">{{ _t('Typography') }}</h3>
    <div class="ins__field">
      <span class="orb-cap">{{ _t('Font') }}</span>
      <CmkDropdown
        :selected-option="element.font_family ?? ''"
        :options="fontOptions"
        :width="'fill'"
        :label="_t('Font')"
        @update:selected-option="emit('patch', { font_family: $event || null })"
      />
    </div>
    <div class="ins__row">
      <label class="ins__num">
        <span class="orb-cap">{{ _t('Size') }}</span>
        <NumberInput
          :model-value="element.font_size"
          min="4"
          max="512"
          @update:model-value="$event !== null && emit('patch', { font_size: $event })"
        />
      </label>
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Style') }}</span>
        <div class="ins__toggles">
          <button
            class="ins__toggle"
            :class="{ 'ins__toggle--on': element.font_weight === 'bold' }"
            :title="_t('Bold')"
            @click="
              emit('patch', { font_weight: element.font_weight === 'bold' ? 'normal' : 'bold' })
            "
          >
            B
          </button>
          <button
            class="ins__toggle ins__toggle--i"
            :class="{ 'ins__toggle--on': element.font_style === 'italic' }"
            :title="_t('Italic')"
            @click="
              emit('patch', { font_style: element.font_style === 'italic' ? 'normal' : 'italic' })
            "
          >
            I
          </button>
        </div>
      </div>
    </div>
    <div class="ins__field">
      <span class="orb-cap">{{ _t('Align') }}</span>
      <div class="ins__toggles">
        <button
          v-for="opt in alignOptions"
          :key="opt.value"
          class="ins__toggle"
          :class="{ 'ins__toggle--on': element.text_align === opt.value }"
          :title="opt.label"
          :aria-label="opt.label"
          :aria-pressed="element.text_align === opt.value"
          @click="emit('patch', { text_align: opt.value })"
        >
          <svg
            class="ins__toggle-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line
              v-for="(ln, i) in alignLines[opt.value]"
              :key="i"
              :x1="ln[0]"
              :y1="6 + i * 4"
              :x2="ln[1]"
              :y2="6 + i * 4"
            />
          </svg>
        </button>
      </div>
    </div>
    <div class="ins__row">
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Color') }}</span>
        <ColorField
          :label="_t('Color')"
          :default-color="tokens['--pres-fg']"
          :value="element.color"
          @set="emit('patch', { color: $event })"
        />
      </div>
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Background') }}</span>
        <ColorField
          :label="_t('Background')"
          :value="element.background"
          @set="emit('patch', { background: $event })"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import NumberInput from '@/components/NumberInput.vue'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'

import type { PresentationTheme, TextElement } from '@/types/api'
import { PRESENTATION_FONTS } from '@/utils/presentationFonts'
import { themeTokens } from '@/utils/presentationThemes'
import usei18n from '@/vendor/cmk/lib/i18n'

import ColorField from '../ColorField.vue'

const { _t } = usei18n()

const props = defineProps<{ element: TextElement; theme: PresentationTheme }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

const tokens = computed(() => themeTokens(props.theme))

const fontOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: PRESENTATION_FONTS.map((f) => ({
    name: f.stack ?? '',
    title: f.stack === null ? _t('Theme default') : f.title
  }))
}))

const alignOptions = computed(() => [
  { label: _t('Left'), value: 'left' },
  { label: _t('Center'), value: 'center' },
  { label: _t('Right'), value: 'right' }
])

// [x1, x2] per text line (y stepped in the template) — drawn as a left/center/
// right-justified stack of rules, the universal text-alignment glyph.
const alignLines: Record<string, [number, number][]> = {
  left: [
    [4, 20],
    [4, 14],
    [4, 20],
    [4, 14]
  ],
  center: [
    [4, 20],
    [7, 17],
    [4, 20],
    [7, 17]
  ],
  right: [
    [4, 20],
    [10, 20],
    [4, 20],
    [10, 20]
  ]
}
</script>

<style scoped>
.ins {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ins__row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.ins__field,
.ins__num {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.ins__toggles {
  display: flex;
  gap: 4px;
}

.ins__toggle {
  width: 30px;
  height: 30px;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  font-weight: 700;
}

.ins__toggle--i {
  font-style: italic;
}

.ins__toggle-icon {
  width: 16px;
  height: 16px;
}

.ins__toggle--on {
  background: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
  border-color: var(--color-corporate-green-50);
}
</style>
