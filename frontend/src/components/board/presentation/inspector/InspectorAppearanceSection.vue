<template>
  <section class="ins">
    <h3 class="orb-section-title">{{ _t('Appearance') }}</h3>
    <div class="ins__row">
      <div v-if="!isConnector" class="ins__field">
        <span class="orb-cap">{{ _t('Fill') }}</span>
        <ColorField
          :label="_t('Fill')"
          :value="element.fill"
          @set="emit('patch', { fill: $event })"
        />
      </div>
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Stroke') }}</span>
        <ColorField
          :label="_t('Stroke')"
          :value="element.stroke"
          @set="emit('patch', { stroke: $event })"
        />
      </div>
      <label class="ins__num">
        <span class="orb-cap">{{ _t('Width') }}</span>
        <NumberInput
          :model-value="element.stroke_width"
          min="0"
          max="64"
          @update:model-value="$event !== null && emit('patch', { stroke_width: $event })"
        />
      </label>
    </div>
    <div class="ins__row">
      <div v-if="!element.flow" class="ins__field">
        <span class="orb-cap">{{ _t('Stroke style') }}</span>
        <CmkToggleButtonGroup
          :model-value="element.dash"
          :options="dashOptions"
          @update:model-value="emit('patch', { dash: $event })"
        />
      </div>
      <div v-else class="ins__field">
        <span class="orb-cap">{{ _t('Stroke style') }}</span>
        <span class="ins__note">{{ _t('Flow animation overrides the stroke style') }}</span>
      </div>
      <label v-if="element.shape === 'rect'" class="ins__num">
        <span class="orb-cap">{{ _t('Radius') }}</span>
        <NumberInput
          :model-value="element.corner_radius"
          min="0"
          @update:model-value="$event !== null && emit('patch', { corner_radius: $event })"
        />
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import NumberInput from '@/components/NumberInput.vue'
import CmkToggleButtonGroup from '@/components/cmk/CmkToggleButtonGroup'

import type { ShapeElement } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

import ColorField from '../ColorField.vue'

const { _t } = usei18n()

const props = defineProps<{ element: ShapeElement }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

const isConnector = computed(
  () => props.element.shape === 'line' || props.element.shape === 'arrow'
)

const dashOptions = computed(() => [
  { label: _t('Solid'), value: 'solid' },
  { label: _t('Dashed'), value: 'dashed' },
  { label: _t('Dotted'), value: 'dotted' }
])
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

.ins__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.ins__num {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 76px;
}

.ins__note {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}
</style>
