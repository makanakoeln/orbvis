<template>
  <section class="ins">
    <h3 class="orb-section-title">{{ _t('Image') }}</h3>
    <div class="ins__field">
      <span class="orb-cap">{{ _t('From image library') }}</span>
      <ImagePicker
        :model-value="storeImageName"
        :placeholder="_t('Choose an image…')"
        @update:model-value="emit('patch', { src: $event || null })"
      />
    </div>
    <div class="ins__field">
      <span class="orb-cap">{{ _t('…or image URL') }}</span>
      <input
        class="orb-field"
        :value="externalSrc"
        :placeholder="_t('https://…')"
        @change="onUrlChange"
      />
    </div>
    <div class="ins__field">
      <span class="orb-cap">{{ _t('Fit') }}</span>
      <CmkToggleButtonGroup
        :model-value="element.fit"
        :options="fitOptions"
        @update:model-value="emit('patch', { fit: $event })"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import CmkToggleButtonGroup from '@/components/cmk/CmkToggleButtonGroup'

import type { ImageElement } from '@/types/api'
import { imageRefName } from '@/utils/presentationElements'
import usei18n from '@/vendor/cmk/lib/i18n'

import ImagePicker from '../../ImagePicker.vue'

const { _t } = usei18n()

const props = defineProps<{ element: ImageElement }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

// Image src is either an image-store filename (bare name) or an external URL.
// The picker reflects only store images; the URL field only external ones.
const storeImageName = computed(() => imageRefName(props.element.src))
const externalSrc = computed(() => {
  const src = props.element.src ?? ''
  return imageRefName(src) ? '' : src
})

const fitOptions = computed(() => [
  { label: _t('Contain'), value: 'contain' },
  { label: _t('Cover'), value: 'cover' },
  { label: _t('Fill'), value: 'fill' }
])

function onUrlChange(e: Event): void {
  emit('patch', { src: (e.target as HTMLInputElement).value || null })
}
</script>

<style scoped>
.ins {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ins__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
