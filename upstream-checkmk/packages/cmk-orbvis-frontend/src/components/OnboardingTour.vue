<template>
  <Teleport to="body">
    <!-- 1. SVG overlay (dimming) -->
    <svg class="orb-tour__overlay" style="z-index: 9998">
      <path fill-rule="evenodd" fill="rgba(0,0,0,0.65)" :d="overlayPath" />
    </svg>

    <!-- 2. Pulsing beacon ring around target element -->
    <div
      v-if="targetRect"
      class="orb-tour__beacon"
      :style="[
        beaconStyle,
        {
          boxShadow: '0 0 0 2px rgb(99 102 241 / 0.8), 0 0 20px 4px rgb(99 102 241 / 0.3)'
        }
      ]"
      style="z-index: 10000"
    >
      <div class="orb-tour__beacon-pulse" style="box-shadow: 0 0 0 2px rgb(129 140 248 / 60%)" />
    </div>

    <!-- 3. Demo scene on canvas step -->
    <OnboardingDemoScene
      v-if="currentStep.selector?.includes('map-canvas') && targetRect"
      :canvas-rect="targetRect"
      style="z-index: 9999"
    />

    <!-- 3b. Settings scene on map-settings step -->
    <OnboardingSettingsScene
      v-if="currentStep.selector?.includes('map-settings') && targetRect"
      style="z-index: 9999"
    />

    <!-- 4. Click-away backdrop (skip on click) -->
    <div class="orb-tour__backdrop" style="z-index: 10000" @click="skip" />

    <!-- 5. Tooltip card -->
    <Transition name="tour-card">
      <div :key="step" class="orb-tour__card" style="z-index: 10003" :style="cardStyle" @click.stop>
        <!-- Step dots -->
        <div class="orb-tour__dots">
          <div
            v-for="i in TOTAL"
            :key="i"
            class="orb-tour__dot"
            :class="
              i < step
                ? 'orb-tour__dot--done'
                : i === step
                  ? 'orb-tour__dot--active'
                  : 'orb-tour__dot--todo'
            "
          />
        </div>

        <div class="orb-tour__body">
          <h3 class="orb-tour__title">
            {{ currentStep.title }}
          </h3>
          <p class="orb-tour__text">
            {{ currentStep.body }}
          </p>
        </div>

        <div class="orb-tour__footer">
          <button class="orb-tour__skip" @click="skip">
            {{ _t('Skip tour') }}
          </button>
          <div class="orb-tour__nav">
            <button v-if="step > 1" class="orb-tour__btn-back" @click="prev">
              {{ _t('Back') }}
            </button>
            <!-- Last step with create-map action -->
            <template v-if="step === TOTAL && showCreateMap">
              <button class="orb-tour__btn-primary" @click="createMap">
                {{ _t('Create first map') }}
              </button>
            </template>
            <!-- Last step without create-map -->
            <button v-else-if="step === TOTAL" class="orb-tour__btn-primary" @click="finish">
              {{ _t('Done') }}
            </button>
            <!-- Intermediate step with selector: click-to-continue hint + Next button -->
            <template v-else-if="currentStep.selector && targetRect">
              <span class="orb-tour__hint">
                {{ _t('Click the highlighted element →') }}
              </span>
              <button class="orb-tour__btn-primary" @click="onClickNext">
                {{ _t('Next') }}
              </button>
            </template>
            <!-- Intermediate step without selector (or target not found): Next button -->
            <button v-else class="orb-tour__btn-primary" @click="onClickNext">
              {{ _t('Next') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 6. Transparent click-catcher over target element (advances step) -->
    <div
      v-if="currentStep.selector && targetRect && step < TOTAL"
      class="orb-tour__catcher"
      :style="beaconStyle"
      style="z-index: 10002"
      @click="onClickCatcher"
    />

    <!-- 7. Completion animation overlay -->
    <Transition name="completion">
      <div v-if="showCompletion" class="orb-tour__completion" style="z-index: 10004">
        <div class="orb-tour__completion-inner">
          <div class="check-circle">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <p class="orb-tour__completion-title">{{ _t("You're all set!") }}</p>
          <p class="orb-tour__completion-subtitle">
            {{ _t('Start exploring OrbVis') }}
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import OnboardingDemoScene from '@/components/OnboardingDemoScene.vue'
import OnboardingSettingsScene from '@/components/OnboardingSettingsScene.vue'

import type { TourStep } from '@/types/tour'
import usei18n from '@cmk/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  steps: TourStep[]
  storageKey: string
  showCreateMap?: boolean
}>()

const emit = defineEmits<{
  close: []
  createMap: []
  stepClick: [step: number]
  stepBack: [step: number]
}>()

// ─── Steps ───────────────────────────────────────────────────────────────────

const step = ref(1)
const TOTAL = computed(() => props.steps.length)
// step always stays within 1..steps.length, so the lookup never misses.
const currentStep = computed(() => props.steps[step.value - 1]!)

// ─── Target rect ─────────────────────────────────────────────────────────────

const targetRect = ref<DOMRect | null>(null)

function measureTarget() {
  const sel = currentStep.value.selector
  if (!sel) {
    targetRect.value = null
    return
  }
  const el = document.querySelector(sel)
  targetRect.value = el ? el.getBoundingClientRect() : null
}

watch(step, () => {
  requestAnimationFrame(measureTarget)
})

function onResize() {
  measureTarget()
}

function onKeyDown(e: KeyboardEvent) {
  if (showCompletion.value) return
  if (e.key === 'ArrowRight' || e.key === 'Enter') {
    e.preventDefault()
    if (step.value < TOTAL.value) {
      if (currentStep.value.selector && targetRect.value) emit('stepClick', step.value)
      next()
    } else {
      finish()
    }
  } else if (e.key === 'ArrowLeft') {
    if (step.value > 1) prev()
  } else if (e.key === 'Escape') {
    skip()
  }
}

onMounted(() => {
  measureTarget()
  window.addEventListener('resize', onResize)
  document.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  document.removeEventListener('keydown', onKeyDown)
})

// ─── SVG overlay path ────────────────────────────────────────────────────────

const PAD = 10
const R = 10

function roundedRectPath(x: number, y: number, w: number, h: number, r: number) {
  return `M${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h - r} Q${x + w},${y + h} ${x + w - r},${y + h} H${x + r} Q${x},${y + h} ${x},${y + h - r} V${y + r} Q${x},${y} ${x + r},${y} Z`
}

const overlayPath = computed(() => {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const outer = `M0,0 H${vw} V${vh} H0 Z`
  const rect = targetRect.value
  if (!rect) return outer

  const x = Math.max(0, rect.left - PAD)
  const y = Math.max(0, rect.top - PAD)
  const w = Math.min(vw - x, rect.width + PAD * 2)
  const h = Math.min(vh - y, rect.height + PAD * 2)
  return `${outer} ${roundedRectPath(x, y, w, h, R)}`
})

// ─── Beacon / click-catcher style ────────────────────────────────────────────

const beaconStyle = computed(() => {
  const rect = targetRect.value
  if (!rect) return {}
  return {
    top: `${Math.max(0, rect.top - PAD)}px`,
    left: `${Math.max(0, rect.left - PAD)}px`,
    width: `${rect.width + PAD * 2}px`,
    height: `${rect.height + PAD * 2}px`
  }
})

// ─── Tooltip position ────────────────────────────────────────────────────────

const CARD_W = 320
const CARD_H = 200
const MARGIN = 16

const cardStyle = computed(() => {
  const rect = targetRect.value
  if (!rect) {
    return { top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }
  }
  const vw = window.innerWidth
  const vh = window.innerHeight

  // Keep card outside the sidebar
  const sidebarEl = document.querySelector('aside')
  const leftBound = sidebarEl ? Math.ceil(sidebarEl.getBoundingClientRect().right) + MARGIN : MARGIN

  let left: number, top: number

  if (rect.right + MARGIN + CARD_W <= vw) {
    left = rect.right + MARGIN
    top = rect.top
  } else if (rect.left - MARGIN - CARD_W >= leftBound) {
    left = rect.left - MARGIN - CARD_W
    top = rect.top
  } else if (rect.bottom + MARGIN + CARD_H <= vh) {
    left = rect.left + (rect.width - CARD_W) / 2
    top = rect.bottom + MARGIN
  } else {
    left = rect.left + (rect.width - CARD_W) / 2
    top = rect.top - MARGIN - CARD_H
  }

  top = Math.max(MARGIN, Math.min(vh - CARD_H - MARGIN, top))
  left = Math.max(leftBound, Math.min(vw - CARD_W - MARGIN, left))
  return { top: `${top}px`, left: `${left}px`, transform: 'none' }
})

// ─── Completion animation ─────────────────────────────────────────────────────

const showCompletion = ref(false)

function showAndClose(callback: () => void) {
  showCompletion.value = true
  setTimeout(() => {
    showCompletion.value = false
    setTimeout(callback, 200)
  }, 1400)
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function markDone() {
  localStorage.setItem(props.storageKey, '1')
}

function next() {
  step.value++
}
function prev() {
  emit('stepBack', step.value)
  step.value--
}
function onClickCatcher() {
  emit('stepClick', step.value)
  next()
}
function onClickNext() {
  if (currentStep.value.selector && targetRect.value) {
    emit('stepClick', step.value)
  }
  next()
}
function skip() {
  markDone()
  emit('close')
}
function finish() {
  markDone()
  showAndClose(() => emit('close'))
}
function createMap() {
  markDone()
  showAndClose(() => emit('createMap'))
}
</script>

<style scoped>
.orb-tour__overlay {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.orb-tour__beacon {
  position: fixed;
  border-radius: 10px;
  pointer-events: none;
}

.orb-tour__beacon-pulse {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  animation: orb-tour-ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;
}

@keyframes orb-tour-ping {
  75%,
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

.orb-tour__backdrop {
  position: fixed;
  inset: 0;
}

.orb-tour__card {
  position: fixed;
  width: 320px;
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 16px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-tour__dots {
  display: flex;
  justify-content: center;
  gap: var(--dimension-4);
  padding: var(--dimension-6) 0 var(--dimension-3);
}

.orb-tour__dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  transition: all 0.3s;
}

.orb-tour__dot--done {
  background: var(--color-corporate-green-50);
}

.orb-tour__dot--active {
  width: 10px;
  height: 10px;
  background: var(--color-corporate-green-50);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-corporate-green-50) 40%, transparent);
}

.orb-tour__dot--todo {
  background: var(--color-pending);
}

.orb-tour__body {
  padding: var(--dimension-4) var(--dimension-7) var(--dimension-5);
}

.orb-tour__title {
  margin-bottom: 6px;
  font-size: var(--font-size-xlarge);
  line-height: 24px;
  font-weight: 700;
  color: var(--text);
}

.orb-tour__text {
  font-size: var(--font-size-large);
  line-height: 1.625;
  color: var(--text-muted);
}

.orb-tour__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--dimension-7) var(--dimension-6);
}

.orb-tour__nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.orb-tour__skip {
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
}

.orb-tour__btn-back {
  padding: 6px var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  border-radius: 8px;
  transition: all 0.15s;
}

.orb-tour__btn-back:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-tour__btn-primary {
  padding: 6px var(--dimension-6);
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 600;
  color: var(--button-primary-text-color, #000);
  background: var(--color-corporate-green-50);
  border-radius: 8px;
  transition: all 0.15s;
}

.orb-tour__btn-primary:hover {
  background: var(--color-corporate-green-60);
}

.orb-tour__hint {
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--color-corporate-green-50);
  user-select: none;
  animation: orb-tour-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes orb-tour-pulse {
  50% {
    opacity: 0.5;
  }
}

.orb-tour__catcher {
  position: fixed;
  cursor: pointer;
  border-radius: 10px;
}

.orb-tour__completion {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 70%);
}

.orb-tour__completion-inner {
  text-align: center;
}

.orb-tour__completion-title {
  font-size: 24px;
  line-height: 32px;
  font-weight: 700;
  color: white;
}

.orb-tour__completion-subtitle {
  margin-top: var(--dimension-3);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

/* ─── Tour card slide-in ─────────────────────────────────────────────────── */
.tour-card-enter-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.tour-card-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

/* ─── Completion overlay ─────────────────────────────────────────────────── */
.completion-enter-active,
.completion-leave-active {
  transition: opacity 0.2s ease;
}

.completion-enter-from,
.completion-leave-to {
  opacity: 0;
}

/* ─── Check circle ───────────────────────────────────────────────────────── */
.check-circle {
  margin: 0 auto var(--dimension-7);
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: #4f46e5;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  animation: check-bounce 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.check-circle svg {
  width: 36px;
  height: 36px;
}

@keyframes check-bounce {
  0% {
    transform: scale(0);
    opacity: 0;
  }

  60% {
    transform: scale(1.2);
  }

  100% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
