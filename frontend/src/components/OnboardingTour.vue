<template>
  <Teleport to="body">
    <!-- Spotlight overlay (pointer-events none so underlying page stays readable) -->
    <svg class="fixed inset-0 w-full h-full pointer-events-none" style="z-index: 9998">
      <path fill-rule="evenodd" fill="rgba(0,0,0,0.65)" :d="overlayPath" />
    </svg>

    <!-- Full-screen click-away layer (below tooltip) -->
    <div class="fixed inset-0" style="z-index: 9999" @click="skip" />

    <!-- Tooltip card -->
    <div
      class="fixed w-80 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-2xl shadow-2xl shadow-black/60 overflow-hidden transition-[top,left] duration-200 ease-out"
      style="z-index: 10000"
      :style="cardStyle"
      @click.stop
    >
      <!-- Progress bar -->
      <div class="h-0.5 bg-[var(--border)]">
        <div
          class="h-full bg-indigo-500 transition-all duration-300"
          :style="{ width: `${(step / TOTAL) * 100}%` }"
        />
      </div>

      <div class="px-5 pt-4 pb-3">
        <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-1.5">
          {{ step }} / {{ TOTAL }}
        </p>
        <h3 class="font-bold text-[var(--text)] text-base mb-1.5">{{ currentStep.title }}</h3>
        <p class="text-sm text-zinc-400 leading-relaxed">{{ currentStep.body }}</p>
      </div>

      <div class="flex items-center justify-between px-5 pb-4">
        <button class="text-xs text-zinc-600 hover:text-zinc-400 transition-colors" @click="skip">
          {{ t('onboarding.skip') }}
        </button>
        <div class="flex items-center gap-1.5">
          <button
            v-if="step > 1"
            class="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
            @click="prev"
          >
            {{ t('onboarding.back') }}
          </button>
          <!-- Last step admin: two actions -->
          <template v-if="step === TOTAL && isAdmin">
            <button
              class="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
              @click="finish"
            >
              {{ t('onboarding.finish') }}
            </button>
            <button
              class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all"
              @click="createBoard"
            >
              {{ t('onboarding.createFirstBoard') }}
            </button>
          </template>
          <!-- Last step non-admin -->
          <button
            v-else-if="step === TOTAL"
            class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all"
            @click="finish"
          >
            {{ t('onboarding.finish') }}
          </button>
          <!-- Not last step -->
          <button
            v-else
            class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all"
            @click="next"
          >
            {{ t('onboarding.next') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const props = defineProps<{
  userId: number
  isAdmin: boolean
}>()

const emit = defineEmits<{
  close: []
  createBoard: []
}>()

// ─── Steps ───────────────────────────────────────────────────────────────────

const step = ref(1)

interface TourStep {
  selector: string | null // data-tour="…"
  title: string
  body: string
}

const steps = computed<TourStep[]>(() => {
  const all: TourStep[] = [
    {
      selector: null,
      title: t('onboarding.step1.title'),
      body: t('onboarding.step1.body'),
    },
    {
      selector: '[data-tour="sidebar-nav"]',
      title: t('onboarding.step2.title'),
      body: props.isAdmin ? t('onboarding.step2.bodyAdmin') : t('onboarding.step2.bodyUser'),
    },
    {
      selector: '[data-tour="boards-grid"]',
      title: t('onboarding.step3.title'),
      body: t('onboarding.step3.body'),
    },
    {
      selector: props.isAdmin ? '[data-tour="new-board"]' : null,
      title: t('onboarding.step4.title'),
      body: props.isAdmin ? t('onboarding.step4.bodyAdmin') : t('onboarding.step4.bodyUser'),
    },
  ]
  return auth.ssoActive || auth.isCheckmkDeployment
    ? all.filter((s) => s.selector !== '[data-tour="sidebar-nav"]')
    : all
})

const TOTAL = computed(() => steps.value.length)
const currentStep = computed(() => steps.value[step.value - 1])

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
  // Tiny delay so Vue renders any v-if changes before we measure
  requestAnimationFrame(measureTarget)
})

function onResize() {
  measureTarget()
}

onMounted(() => {
  measureTarget()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})

// ─── SVG overlay path ────────────────────────────────────────────────────────

const PAD = 10 // px padding around the highlight
const R = 10 // border-radius of the hole

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

// ─── Tooltip position ────────────────────────────────────────────────────────

const CARD_W = 320
const CARD_H = 200 // conservative estimate
const MARGIN = 16

const cardStyle = computed(() => {
  const rect = targetRect.value
  if (!rect) {
    return { top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }
  }
  const vw = window.innerWidth
  const vh = window.innerHeight

  let left: number, top: number

  if (rect.right + MARGIN + CARD_W <= vw) {
    // Right of target
    left = rect.right + MARGIN
    top = rect.top
  } else if (rect.left - MARGIN - CARD_W >= 0) {
    // Left of target
    left = rect.left - MARGIN - CARD_W
    top = rect.top
  } else if (rect.bottom + MARGIN + CARD_H <= vh) {
    // Below target
    left = Math.max(MARGIN, rect.left)
    top = rect.bottom + MARGIN
  } else {
    // Above target
    left = Math.max(MARGIN, rect.left)
    top = rect.top - MARGIN - CARD_H
  }

  top = Math.max(MARGIN, Math.min(vh - CARD_H - MARGIN, top))
  left = Math.max(MARGIN, Math.min(vw - CARD_W - MARGIN, left))
  return { top: `${top}px`, left: `${left}px`, transform: 'none' }
})

// ─── Navigation ──────────────────────────────────────────────────────────────

function markDone() {
  localStorage.setItem(`orbvis_onboarded_${props.userId}`, '1')
}

function next() {
  step.value++
}
function prev() {
  step.value--
}
function skip() {
  markDone()
  emit('close')
}
function finish() {
  markDone()
  emit('close')
}
function createBoard() {
  markDone()
  emit('createBoard')
}
</script>
