<template>
  <div class="psp" :style="outerStyle">
    <div class="psp__stage" :style="stageStyle">
      <div class="psp__bg" />
      <svg class="psp__connectors" :style="{ width: `${width}px`, height: `${height}px` }">
        <line
          v-for="c in connectors"
          :key="c.el.id"
          :x1="c.start.x"
          :y1="c.start.y"
          :x2="c.end.x"
          :y2="c.end.y"
          stroke="var(--pres-shape-stroke)"
          :stroke-width="c.el.stroke_width * 2"
          stroke-linecap="round"
        />
      </svg>
      <div v-for="el in boxElements" :key="el.id" class="psp__el" :style="elStyle(el)">
        <PresentationElementView :element="el" :state="undefined" :sample-state="sampleFor(el)" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { ObjectState, PresentationElement, PresentationTheme, ShapeElement } from '@/types/api'
import { isUnboundSlot, sampleStateFor } from '@/utils/presentationSampleState'
import { themeTokens } from '@/utils/presentationThemes'

import PresentationElementView from './PresentationElementView.vue'

const props = withDefaults(
  defineProps<{
    elements: PresentationElement[]
    theme: PresentationTheme
    width?: number
    height?: number
    thumbWidth?: number
  }>(),
  { width: 1920, height: 1080, thumbWidth: 248 }
)

const scale = computed(() => props.thumbWidth / props.width)

const outerStyle = computed(() => ({
  width: `${props.thumbWidth}px`,
  height: `${Math.round(props.height * scale.value)}px`
}))

const stageStyle = computed(() => ({
  ...themeTokens(props.theme),
  width: `${props.width}px`,
  height: `${props.height}px`,
  transform: `scale(${scale.value})`,
  transformOrigin: 'top left'
}))

function isConnector(el: PresentationElement): el is ShapeElement {
  return el.kind === 'shape' && (el.shape === 'line' || el.shape === 'arrow')
}

function centerOf(id: string | null | undefined): { x: number; y: number } | null {
  const el = props.elements.find((e) => e.id === id)
  if (!el) return null
  return { x: el.x + el.w / 2, y: el.y + el.h / 2 }
}

const connectors = computed(() =>
  props.elements.filter(isConnector).map((el) => ({
    el,
    start: centerOf(el.start_ref) ?? { x: el.x, y: el.y },
    end: centerOf(el.end_ref) ?? { x: el.x + el.w, y: el.y + el.h }
  }))
)

const boxElements = computed(() =>
  [...props.elements]
    .filter((e) => !isConnector(e) && e.kind !== 'group' && !e.hidden)
    .sort((a, b) => a.z - b.z)
)

function elStyle(el: PresentationElement): Record<string, string> {
  return {
    left: `${el.x}px`,
    top: `${el.y}px`,
    width: `${el.w}px`,
    height: `${el.h}px`,
    opacity: String(el.opacity),
    transform: el.rotation ? `rotate(${el.rotation}deg)` : 'none',
    zIndex: String(el.z)
  }
}

function sampleFor(el: PresentationElement): ObjectState | undefined {
  return isUnboundSlot(el) ? sampleStateFor(el) : undefined
}
</script>

<style scoped>
.psp {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  pointer-events: none;
}

.psp__stage {
  position: absolute;
  top: 0;
  left: 0;
}

.psp__bg {
  position: absolute;
  inset: 0;
  background: var(--pres-bg);
}

.psp__connectors {
  position: absolute;
  inset: 0;
  overflow: visible;
}

.psp__el {
  position: absolute;
  transform-origin: center center;
}
</style>
