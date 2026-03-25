<template>
  <Teleport to="body">
    <!-- 1. SVG overlay (dimming) -->
    <svg class="fixed inset-0 w-full h-full pointer-events-none" style="z-index: 9998">
      <path fill-rule="evenodd" fill="rgba(0,0,0,0.65)" :d="overlayPath" />
    </svg>

    <!-- 2. Pulsing beacon ring around target element -->
    <div
      v-if="targetRect"
      class="fixed rounded-[10px] pointer-events-none"
      :style="[
        beaconStyle,
        { boxShadow: '0 0 0 2px rgb(99 102 241 / 0.8), 0 0 20px 4px rgb(99 102 241 / 0.3)' },
      ]"
      style="z-index: 9999"
    >
      <div
        class="absolute inset-0 rounded-[10px] animate-ping"
        style="box-shadow: 0 0 0 2px rgb(129 140 248 / 60%)"
      />
    </div>

    <!-- 3. Demo scene on canvas step -->
    <OnboardingDemoScene
      v-if="currentStep.selector === '[data-tour=\'board-canvas\']' && targetRect"
      :canvas-rect="targetRect"
      style="z-index: 9999"
    />

    <!-- 4. Click-away backdrop (skip on click) -->
    <div class="fixed inset-0" style="z-index: 10000" @click="skip" />

    <!-- 5. Tooltip card -->
    <Transition name="tour-card">
      <div
        :key="step"
        class="fixed w-80 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-2xl shadow-2xl shadow-black/60 overflow-hidden"
        style="z-index: 10001"
        :style="cardStyle"
        @click.stop
      >
        <!-- Step dots -->
        <div class="flex justify-center gap-2 pt-4 pb-1">
          <div
            v-for="i in TOTAL"
            :key="i"
            class="rounded-full transition-all duration-300"
            :class="
              i < step
                ? 'w-2 h-2 bg-indigo-500'
                : i === step
                  ? 'w-2.5 h-2.5 bg-indigo-400 ring-2 ring-indigo-400/40'
                  : 'w-2 h-2 bg-zinc-600'
            "
          />
        </div>

        <div class="px-5 pt-2 pb-3">
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
            <!-- Last step with create-board action -->
            <template v-if="step === TOTAL && showCreateBoard">
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
            <!-- Last step without create-board -->
            <button
              v-else-if="step === TOTAL"
              class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all"
              @click="finish"
            >
              {{ t('onboarding.finish') }}
            </button>
            <!-- Intermediate step with selector: click-to-continue hint -->
            <span
              v-else-if="currentStep.selector && targetRect"
              class="text-xs text-indigo-400 animate-pulse select-none"
            >
              {{ t('onboarding.clickToContinue') }}
            </span>
            <!-- Intermediate step without selector (or target not found): Next button -->
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
    </Transition>

    <!-- 6. Transparent click-catcher over target element (advances step) -->
    <div
      v-if="currentStep.selector && targetRect && step < TOTAL"
      class="fixed cursor-pointer rounded-[10px]"
      :style="beaconStyle"
      style="z-index: 10002"
      @click="onClickCatcher"
    />

    <!-- 7. Completion animation overlay -->
    <Transition name="completion">
      <div
        v-if="showCompletion"
        class="fixed inset-0 flex items-center justify-center bg-black/70"
        style="z-index: 10003"
      >
        <div class="text-center">
          <div class="check-circle mx-auto mb-5">
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
          <p class="text-2xl font-bold text-white">{{ t('onboarding.complete') }}</p>
          <p class="text-sm text-zinc-400 mt-1">{{ t('onboarding.completeSubtitle') }}</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import OnboardingDemoScene from '@/components/OnboardingDemoScene.vue';
import type { TourStep } from '@/types/tour';

const { t } = useI18n();

const props = defineProps<{
  steps: TourStep[];
  storageKey: string;
  showCreateBoard?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  createBoard: [];
  stepClick: [step: number];
}>();

// ─── Steps ───────────────────────────────────────────────────────────────────

const step = ref(1);
const TOTAL = computed(() => props.steps.length);
const currentStep = computed(() => props.steps[step.value - 1]);

// ─── Target rect ─────────────────────────────────────────────────────────────

const targetRect = ref<DOMRect | null>(null);

function measureTarget() {
  const sel = currentStep.value.selector;
  if (!sel) {
    targetRect.value = null;
    return;
  }
  const el = document.querySelector(sel);
  targetRect.value = el ? el.getBoundingClientRect() : null;
}

watch(step, () => {
  requestAnimationFrame(measureTarget);
});

function onResize() {
  measureTarget();
}

function onKeyDown(e: KeyboardEvent) {
  if (showCompletion.value) return;
  if (e.key === 'ArrowRight' || e.key === 'Enter') {
    e.preventDefault();
    if (step.value < TOTAL.value) {
      if (currentStep.value.selector && targetRect.value) emit('stepClick', step.value);
      next();
    } else {
      finish();
    }
  } else if (e.key === 'ArrowLeft') {
    if (step.value > 1) prev();
  } else if (e.key === 'Escape') {
    skip();
  }
}

onMounted(() => {
  measureTarget();
  window.addEventListener('resize', onResize);
  document.addEventListener('keydown', onKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('resize', onResize);
  document.removeEventListener('keydown', onKeyDown);
});

// ─── SVG overlay path ────────────────────────────────────────────────────────

const PAD = 10;
const R = 10;

function roundedRectPath(x: number, y: number, w: number, h: number, r: number) {
  return `M${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h - r} Q${x + w},${y + h} ${x + w - r},${y + h} H${x + r} Q${x},${y + h} ${x},${y + h - r} V${y + r} Q${x},${y} ${x + r},${y} Z`;
}

const overlayPath = computed(() => {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const outer = `M0,0 H${vw} V${vh} H0 Z`;
  const rect = targetRect.value;
  if (!rect) return outer;

  const x = Math.max(0, rect.left - PAD);
  const y = Math.max(0, rect.top - PAD);
  const w = Math.min(vw - x, rect.width + PAD * 2);
  const h = Math.min(vh - y, rect.height + PAD * 2);
  return `${outer} ${roundedRectPath(x, y, w, h, R)}`;
});

// ─── Beacon / click-catcher style ────────────────────────────────────────────

const beaconStyle = computed(() => {
  const rect = targetRect.value;
  if (!rect) return {};
  return {
    top: `${Math.max(0, rect.top - PAD)}px`,
    left: `${Math.max(0, rect.left - PAD)}px`,
    width: `${rect.width + PAD * 2}px`,
    height: `${rect.height + PAD * 2}px`,
  };
});

// ─── Tooltip position ────────────────────────────────────────────────────────

const CARD_W = 320;
const CARD_H = 200;
const MARGIN = 16;

const cardStyle = computed(() => {
  const rect = targetRect.value;
  if (!rect) {
    return { top: '50%', left: '50%', transform: 'translate(-50%,-50%)' };
  }
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let left: number, top: number;

  if (rect.right + MARGIN + CARD_W <= vw) {
    left = rect.right + MARGIN;
    top = rect.top;
  } else if (rect.left - MARGIN - CARD_W >= 0) {
    left = rect.left - MARGIN - CARD_W;
    top = rect.top;
  } else if (rect.bottom + MARGIN + CARD_H <= vh) {
    left = Math.max(MARGIN, rect.left);
    top = rect.bottom + MARGIN;
  } else {
    left = Math.max(MARGIN, rect.left);
    top = rect.top - MARGIN - CARD_H;
  }

  top = Math.max(MARGIN, Math.min(vh - CARD_H - MARGIN, top));
  left = Math.max(MARGIN, Math.min(vw - CARD_W - MARGIN, left));
  return { top: `${top}px`, left: `${left}px`, transform: 'none' };
});

// ─── Completion animation ─────────────────────────────────────────────────────

const showCompletion = ref(false);

function showAndClose(callback: () => void) {
  showCompletion.value = true;
  setTimeout(() => {
    showCompletion.value = false;
    setTimeout(callback, 200);
  }, 1400);
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function markDone() {
  localStorage.setItem(props.storageKey, '1');
}

function next() {
  step.value++;
}
function prev() {
  step.value--;
}
function onClickCatcher() {
  emit('stepClick', step.value);
  next();
}
function skip() {
  markDone();
  emit('close');
}
function finish() {
  markDone();
  showAndClose(() => emit('close'));
}
function createBoard() {
  markDone();
  showAndClose(() => emit('createBoard'));
}
</script>

<style scoped>
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
