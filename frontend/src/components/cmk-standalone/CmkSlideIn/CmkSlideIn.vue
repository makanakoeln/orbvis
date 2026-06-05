<!--
OrbVis-native CmkSlideIn, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. Same reka-ui Dialog stack as upstream
plus a local copy of the stack-priority helper.
-->
<script setup lang="ts">
import { DialogContent, DialogOverlay, DialogPortal, DialogRoot } from 'reka-ui'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import { useSlideInStack } from './useSlideInStack'

export interface SlideInVariants {
  size?: 'medium' | 'small'
  borderColor?: 'default' | 'purple'
}

export interface CmkSlideInProps {
  open: boolean
  size?: SlideInVariants['size']
  isIndexPage?: boolean | undefined
  ariaLabel?: string | undefined
  stackPriority?: number | undefined
  borderColor?: SlideInVariants['borderColor']
  initialFocusTarget?: HTMLElement | undefined
}

const props = withDefaults(defineProps<CmkSlideInProps>(), {
  size: 'medium',
  borderColor: 'default'
})
const emit = defineEmits(['close'])

const dialogContentRef = ref<InstanceType<typeof DialogContent>>()
const { isTopMost, register, unregister } = useSlideInStack(props.stackPriority ?? null)
const effectiveOpen = computed(() => props.open && isTopMost.value)

watch(
  () => props.open,
  (isOpen) => (isOpen ? register() : unregister()),
  { immediate: true }
)

watch(effectiveOpen, async (isOpen) => {
  if (!isOpen) return
  await nextTick(() => {
    const target = props.initialFocusTarget ?? dialogContentRef.value?.$el
    if (target instanceof HTMLElement) target.focus()
  })
})

onBeforeUnmount(() => unregister())
</script>

<template>
  <DialogRoot v-if="open" :open="effectiveOpen" :modal="!isIndexPage">
    <DialogPortal :to="isIndexPage ? '#content_area' : 'body'">
      <DialogOverlay
        v-if="!isIndexPage && effectiveOpen"
        class="orb-slide-in__overlay"
        @click="emit('close')"
      />
      <div v-if="effectiveOpen" class="orb-slide-in__overlay" @click="emit('close')" />
      <DialogContent
        ref="dialogContentRef"
        class="orb-slide-in__container"
        :class="[`orb-slide-in--size-${size}`, `orb-slide-in--border-${borderColor}`]"
        :aria-describedby="undefined"
        :aria-label="ariaLabel"
        @escape-key-down="emit('close')"
        @open-auto-focus.prevent
        @close-auto-focus.prevent
      >
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style>
body:has(.orb-slide-in__container) {
  overflow: hidden;
}
</style>

<style scoped>
.orb-slide-in__container {
  width: 80%;
  max-width: 1024px;
  display: flex;
  flex-direction: column;
  position: absolute;
  z-index: 1000;
  top: 0;
  right: 0;
  bottom: 0;
  border-left: 4px solid var(--color-corporate-green-50, #15d1a0);
  background: var(--default-bg-color, var(--ux-theme-2, #20272e));
}

.orb-slide-in__container:focus,
.orb-slide-in__container:focus-visible {
  outline: none;
  box-shadow: none;
}

.orb-slide-in--size-small {
  max-width: 768px;
}

.orb-slide-in--border-purple {
  border-left-color: #a855f7;
}

.orb-slide-in__container[data-state='open'] {
  animation: orb-slide-in-show 0.2s ease-in-out;
}

.orb-slide-in__container[data-state='closed'] {
  animation: orb-slide-in-hide 0.2s ease-in-out;
}

@media screen and (width <= 1024px) {
  .orb-slide-in--size-medium {
    width: 100%;
    max-width: 100%;
  }
}

@media screen and (width <= 768px) {
  .orb-slide-in--size-small {
    width: 100%;
    max-width: 100%;
  }
}

@keyframes orb-slide-in-show {
  from {
    opacity: 0;
    transform: translate(50%, 0%);
  }

  to {
    opacity: 1;
    transform: translate(0%, 0%);
  }
}

@keyframes orb-slide-in-hide {
  from {
    opacity: 1;
    transform: translate(0%, 0%);
  }

  to {
    opacity: 0;
    transform: translate(50%, 0%);
  }
}

.orb-slide-in__overlay {
  backdrop-filter: blur(1.5px);
  position: absolute;
  inset: 0;
  background: rgb(0 0 0 / 30%);
  animation: orb-slide-in-overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 999;
}

@keyframes orb-slide-in-overlay-show {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}
</style>
