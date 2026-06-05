<!--
OrbVis-native CmkSlideInDialog, swapped in for the vendored variant
when VITE_BUILD_TARGET=standalone. Uses the standalone CmkSlideIn for
the panel chrome and renders the close button as a plain × glyph.
-->
<script setup lang="ts">
import { DialogClose, DialogTitle } from 'reka-ui'
import { computed, ref } from 'vue'

import type { SlideInVariants } from '@/components/cmk-standalone/CmkSlideIn/CmkSlideIn.vue'
import CmkSlideIn from '@/components/cmk-standalone/CmkSlideIn/CmkSlideIn.vue'
import CmkScrollContainer from '@/components/cmk/CmkScrollContainer'
import CmkHeading from '@/components/cmk/typography/CmkHeading'

export interface CmkSlideInDialogProps {
  open: boolean
  size?: SlideInVariants['size']
  isIndexPage?: boolean | undefined
  stackPriority?: number | undefined
  header?: {
    title: string
    icon?: unknown
    closeButton: boolean
  }
  borderColor?: SlideInVariants['borderColor']
}
defineProps<CmkSlideInDialogProps>()
const emit = defineEmits(['close'])

const scrollContainerRef = ref<InstanceType<typeof CmkScrollContainer>>()
const scrollContainerEl = computed(() => {
  const el = scrollContainerRef.value?.$el
  return el instanceof HTMLElement ? el : undefined
})
</script>

<template>
  <CmkSlideIn
    :aria-label="header?.title"
    :open="open"
    :is-index-page="isIndexPage"
    :size="size"
    :stack-priority="stackPriority"
    :border-color="borderColor"
    :initial-focus-target="scrollContainerEl"
    @close="emit('close')"
  >
    <DialogTitle v-if="header" class="orb-slide-in-dialog__title">
      <CmkHeading type="h1" class="orb-slide-in-dialog__title-header">
        {{ header.title }}
      </CmkHeading>
      <!-- @vue-ignore @click is not a property of DialogClose -->
      <DialogClose
        v-if="header.closeButton"
        class="orb-slide-in-dialog__close"
        aria-label="Close"
        @click="emit('close')"
      >
        ×
      </DialogClose>
    </DialogTitle>

    <CmkScrollContainer
      ref="scrollContainerRef"
      type="outer"
      class="orb-slide-in-dialog__content"
      tabindex="0"
      role="region"
      :aria-label="header?.title ?? 'Content'"
    >
      <slot />
    </CmkScrollContainer>
  </CmkSlideIn>
</template>

<style scoped>
.orb-slide-in-dialog__title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px;
}

.orb-slide-in-dialog__title-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.orb-slide-in-dialog__content {
  padding: 0 20px;
}

.orb-slide-in-dialog__close {
  background: none;
  border: none;
  color: var(--font-color, #f4f4f5);
  margin: 0;
  padding: 0 8px;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}
</style>
