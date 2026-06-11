<template>
  <!-- Shape -->
  <template v-if="element.kind === 'shape'">
    <svg
      class="pres-el__svg"
      :width="element.w"
      :height="element.h"
      :viewBox="`0 0 ${element.w} ${element.h}`"
      preserveAspectRatio="none"
    >
      <rect
        v-if="element.shape === 'rect'"
        :x="strokeInset"
        :y="strokeInset"
        :width="Math.max(0, element.w - element.stroke_width)"
        :height="Math.max(0, element.h - element.stroke_width)"
        :rx="element.corner_radius"
        :fill="fillColor"
        :stroke="strokeColor"
        :stroke-width="element.stroke_width"
        :stroke-dasharray="dashArray"
      />
      <ellipse
        v-else-if="element.shape === 'ellipse'"
        :cx="element.w / 2"
        :cy="element.h / 2"
        :rx="Math.max(0, element.w / 2 - element.stroke_width / 2)"
        :ry="Math.max(0, element.h / 2 - element.stroke_width / 2)"
        :fill="fillColor"
        :stroke="strokeColor"
        :stroke-width="element.stroke_width"
        :stroke-dasharray="dashArray"
      />
      <template v-else>
        <line
          :x1="0"
          :y1="element.h / 2"
          :x2="element.shape === 'arrow' ? element.w - 12 : element.w"
          :y2="element.h / 2"
          :stroke="strokeColor"
          :stroke-width="element.stroke_width"
          :stroke-dasharray="dashArray"
          stroke-linecap="round"
        />
        <polygon
          v-if="element.shape === 'arrow'"
          :points="`${element.w - 14},${element.h / 2 - 8} ${element.w},${element.h / 2} ${element.w - 14},${element.h / 2 + 8}`"
          :fill="strokeColor"
        />
      </template>
    </svg>
    <div v-if="shapeLabelShow" class="pres-el__shape-label" :style="shapeLabelStyle">
      {{ shapeLabelText }}
    </div>
  </template>

  <!-- Text -->
  <div
    v-else-if="element.kind === 'text'"
    ref="textRef"
    class="pres-el__text"
    :class="{ 'pres-el__text--editing': editingText }"
    :contenteditable="editingText"
    :style="textStyle"
    @blur="onTextBlur"
    @keydown.stop
    @pointerdown="editingText && $event.stopPropagation()"
  >
    {{ element.text }}
  </div>

  <!-- Image -->
  <div v-else-if="element.kind === 'image'" class="pres-el__image">
    <img v-if="element.src" :src="imageSrc" :alt="element.alt ?? ''" :style="imageStyle" />
    <div v-else class="pres-el__image-empty">
      <span>{{ _t('No image') }}</span>
    </div>
  </div>

  <!-- Group: only a faint bounds hint while editing -->
  <div v-else-if="element.kind === 'group'" class="pres-el__group" />

  <!-- Data (live status) -->
  <div
    v-else
    class="pres-el__data"
    :style="dataBoxStyle"
    :class="{ 'pres-el__data--unbound': !isBoundElement(element) }"
  >
    <div class="pres-el__data-body">
      <GadgetRenderer
        v-if="element.display.mode === 'gadget' && (isBoundElement(element) || sampleState)"
        :type="effectiveGadgetType"
        :metric="element.display.gadget_metric ?? sampleMetric"
        :state="effectiveState"
        :size="gadgetSize"
        :perfometer="perfometer"
        :metric-units="metricUnits"
      />
      <div
        v-else-if="element.display.mode === 'text'"
        class="pres-el__data-text"
        :style="{ color: stateClr }"
      >
        {{ stateText }}
      </div>
      <img
        v-else-if="element.display.image"
        class="pres-el__data-img"
        :src="resolveImageRef(element.display.image)"
        :alt="''"
        :style="{
          width: `${iconSize}px`,
          height: `${iconSize}px`,
          filter: `drop-shadow(0 0 ${Math.max(2, iconSize * 0.12)}px ${stateClr})`
        }"
      />
      <div
        v-else
        class="pres-el__data-icon"
        :style="{
          width: `${iconSize}px`,
          height: `${iconSize}px`,
          background: stateClr,
          boxShadow: `0 0 ${iconSize * 0.5}px 1px ${stateClr}66`
        }"
      />
    </div>
    <div v-if="showLabel" class="pres-el__data-label" :style="labelStyle">
      {{ labelText }}
    </div>
    <div v-if="sampleState && !isBoundElement(element)" class="pres-el__sample">
      {{ _t('Sample') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import { useMetricUnits } from '@/composables/useMetricUnits'
import { usePerfometer } from '@/composables/usePerfometer'
import type { ObjectState, PresentationElement } from '@/types/api'
import { resolveImageRef } from '@/utils/presentationElements'
import { bindingLabel, isBoundElement, isMetriclessBinding } from '@/utils/presentationSampleState'
import { stateColor } from '@/utils/stateColors'
import usei18n from '@/vendor/cmk/lib/i18n'

import GadgetRenderer from '../GadgetRenderer.vue'

const { _t } = usei18n()

const props = defineProps<{
  element: PresentationElement
  state: ObjectState | undefined
  // Effective connection for the element's binding (element override or board
  // default) — needed for the CMK perfometer lookup behind gauge/bar gadgets.
  connectionId?: string | null
  // Demo data for an unbound data slot in the editor — never set in view mode.
  sampleState?: ObjectState | undefined
  editingText?: boolean
}>()

const emit = defineEmits<{ 'text-change': [string] }>()

const textRef = ref<HTMLElement | null>(null)

// Resolve a null color to the theme's CSS variable so theme switches recolor
// every element that uses the default.
function resolve(color: string | null | undefined, fallbackVar: string): string {
  return color && color.length > 0 ? color : `var(${fallbackVar})`
}

// Live state when bound, sample data when previewing an unbound slot.
const effectiveState = computed(() => props.state ?? props.sampleState)

// Group/BI bindings have a state but no perf metrics — a gauge or bar would
// permanently render "—", so they fall back to the state light.
const effectiveGadgetType = computed(() => {
  const el = props.element
  if (el.kind !== 'data') return 'gauge'
  return isMetriclessBinding(el) ? 'trafficlight' : (el.display.gadget_type ?? 'gauge')
})

// CMK perfometer behind gauge/bar gadgets — fills the dial when the raw
// perf_data has no max and supplies the CMK-formatted caption. Only plain
// host/service bindings have one; groups, BI and traffic lights don't.
const gadgetBinding = {
  connectionId: () => props.connectionId,
  hostName: () => (props.element.kind === 'data' ? props.element.host_name : null),
  serviceDescription: () =>
    props.element.kind === 'data' ? props.element.service_description : null,
  perfData: () => props.state?.perf_data,
  enabled: () =>
    props.element.kind === 'data' &&
    props.element.display.mode === 'gadget' &&
    effectiveGadgetType.value !== 'trafficlight'
}
const perfometer = usePerfometer(gadgetBinding)
// Registered display units so the readout matches the Checkmk GUI.
const metricUnits = useMetricUnits(gadgetBinding)
// The sample perf_data always carries exactly one metric; hand its name to the
// gadget so an unbound preview renders a value instead of an empty dial.
const sampleMetric = computed(() => {
  const pd = props.sampleState?.perf_data ?? ''
  return pd.split('=')[0] || null
})

// A bound shape colours its primary surface by the live state — fill for
// rect/ellipse, stroke for line/arrow — overriding the manual colour. An
// unbound data-slot shape previews with its sample state the same way.
const shapeStateColor = computed(() =>
  props.element.kind === 'shape' && (isBoundElement(props.element) || props.sampleState)
    ? stateColor(effectiveState.value?.state)
    : null
)

const fillColor = computed(() => {
  const el = props.element
  if (el.kind !== 'shape') return 'none'
  if (el.shape === 'line' || el.shape === 'arrow') return 'none'
  if (shapeStateColor.value) return shapeStateColor.value
  return resolve(el.fill, '--pres-shape-fill')
})
const strokeColor = computed(() => {
  const el = props.element
  if (el.kind !== 'shape') return 'none'
  if ((el.shape === 'line' || el.shape === 'arrow') && shapeStateColor.value)
    return shapeStateColor.value
  return resolve(el.stroke, '--pres-shape-stroke')
})

const shapeLabelShow = computed(
  () => props.element.kind === 'shape' && (props.element.label?.show ?? false)
)
const shapeLabelText = computed(() => {
  const el = props.element
  if (el.kind !== 'shape') return ''
  return el.label?.text || effectiveState.value?.state || bindingLabel(el) || ''
})
const shapeLabelStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'shape' || !el.label) return {}
  return {
    color: resolve(el.label.color, '--pres-fg'),
    background: el.label.background ?? 'transparent',
    fontSize: `${el.label.size}px`,
    fontWeight: el.label.weight ?? 'normal',
    textAlign: el.label.align ?? 'center'
  }
})
const strokeInset = computed(() =>
  props.element.kind === 'shape' ? props.element.stroke_width / 2 : 0
)
const dashArray = computed(() => {
  if (props.element.kind !== 'shape') return undefined
  const w = props.element.stroke_width
  if (props.element.dash === 'dashed') return `${w * 3} ${w * 2}`
  if (props.element.dash === 'dotted') return `${w} ${w * 1.5}`
  return undefined
})

const textStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'text') return {}
  return {
    color: resolve(el.color, '--pres-fg'),
    background: el.background ?? 'transparent',
    fontFamily: el.font_family ?? 'var(--pres-font)',
    fontSize: `${el.font_size}px`,
    fontWeight: el.font_weight,
    fontStyle: el.font_style,
    textAlign: el.text_align,
    lineHeight: String(el.line_height),
    letterSpacing: `${el.letter_spacing}px`
  }
})

// A bare store filename resolves to its image URL; an external URL is used verbatim.
const imageSrc = computed(() =>
  props.element.kind === 'image' ? resolveImageRef(props.element.src) : ''
)

const imageStyle = computed(() => ({
  objectFit:
    props.element.kind === 'image' ? (props.element.fit as 'cover' | 'contain' | 'fill') : 'contain'
}))

// Size the gadget to the card minus the label, accounting for how tall each
// gadget renders per unit size — the traffic light stacks three bulbs (~1.85×),
// the gauge is a half-disc (~0.7×), the bar a thin track (~0.55×). Without this
// a traffic light overflows its card.
const gadgetSize = computed(() => {
  const el = props.element
  if (el.kind !== 'data') return 40
  const labelH = (el.label?.show ?? false) ? 30 : 0
  const availW = el.w - 28
  const availH = el.h - labelH - 24
  const gt = effectiveGadgetType.value
  const hFactor = gt === 'trafficlight' ? 1.85 : gt === 'bar' ? 0.55 : 0.7
  return Math.max(36, Math.min(availW, availH / hFactor))
})

const iconSize = computed(() => {
  const el = props.element
  if (el.kind !== 'data') return 36
  const labelH = (el.label?.show ?? false) ? 30 : 0
  return Math.max(20, Math.min(96, Math.min(el.w - 28, el.h - labelH - 24) * 0.55))
})

const stateClr = computed(() => stateColor(effectiveState.value?.state))
const stateText = computed(() => effectiveState.value?.state ?? _t('PENDING'))

const dataBoxStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'data') return {}
  return {
    background: el.fill ? el.fill : 'var(--pres-shape-fill)',
    border: `2px solid ${stateClr.value}`
  }
})

const showLabel = computed(
  () => props.element.kind === 'data' && (props.element.label?.show ?? false)
)
const labelText = computed(() => {
  const el = props.element
  if (el.kind !== 'data') return ''
  // An explicit element name (e.g. the BI aggregation title stamped on bind)
  // beats the raw binding identifier.
  return (
    el.label?.text ||
    el.name ||
    bindingLabel(el) ||
    (props.sampleState ? _t('Sample') : _t('Unbound'))
  )
})
const labelStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'data' || !el.label) return {}
  return {
    color: resolve(el.label.color, '--pres-fg'),
    background: el.label.background ?? 'transparent',
    fontSize: `${el.label.size}px`,
    fontWeight: el.label.weight ?? 'normal',
    textAlign: el.label.align ?? 'center'
  }
})

// Focus + select the text when inline editing starts.
watch(
  () => props.editingText,
  async (on) => {
    if (!on) return
    await nextTick()
    const el = textRef.value
    if (!el) return
    el.focus()
    const range = document.createRange()
    range.selectNodeContents(el)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
  }
)

// Always report the text on blur (even unchanged) so the parent reliably ends
// editing — it commits only on a real change. Without this, blurring a freshly
// added text box whose text is untouched would leave the canvas stuck in edit
// mode (no deselect, no selecting/moving other elements).
function onTextBlur(): void {
  if (props.element.kind !== 'text' || !textRef.value) return
  emit('text-change', textRef.value.innerText)
}
</script>

<style scoped>
.pres-el__svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

/* Centered state label for a bound shape. Lines are only a few px tall, so it
   overflows the box (visible) and sits readably on top via its pill. */
.pres-el__shape-label {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  padding: 1px 6px;
  border-radius: 6px;
  line-height: 1.2;
  white-space: nowrap;
  pointer-events: none;
}

.pres-el__text {
  width: 100%;
  height: 100%;
  outline: none;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.pres-el__text--editing {
  cursor: text;
  box-shadow: 0 0 0 1px var(--pres-accent);
}

.pres-el__image,
.pres-el__image img {
  width: 100%;
  height: 100%;
}

.pres-el__image img {
  display: block;
}

.pres-el__image-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--pres-muted);
  color: var(--pres-muted);
  font-size: 13px;
}

.pres-el__group {
  width: 100%;
  height: 100%;
}

.pres-el__data {
  width: 100%;
  height: 100%;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  box-sizing: border-box;
  overflow: hidden;
}

.pres-el__data--unbound {
  opacity: 0.7;
  border-style: dashed !important;
}

.pres-el__data-body {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 0;
}

.pres-el__data-icon {
  width: 36px;
  height: 36px;
  border-radius: 9999px;
}

.pres-el__data-img {
  object-fit: contain;
}

.pres-el__data-text {
  font-weight: 700;
  font-size: 20px;
}

.pres-el__data-label {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Editor-only badge marking a slot that previews with sample data. */
.pres-el__sample {
  position: absolute;
  top: 4px;
  right: 6px;
  padding: 0 5px;
  border: 1px dashed var(--pres-muted);
  border-radius: 5px;
  font-size: 10px;
  font-family: var(--pres-font, sans-serif);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--pres-muted);
  pointer-events: none;
}
</style>
