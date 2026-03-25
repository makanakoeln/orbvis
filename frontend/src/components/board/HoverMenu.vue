<template>
  <div class="fixed z-50 pointer-events-none" :style="{ left: `${x}px`, top: `${y}px` }">
    <div
      class="bg-[var(--bg-glass)] backdrop-blur-md ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-xl p-3.5 min-w-52 max-w-72"
    >
      <!-- Custom template — sanitized via DOMPurify before rendering -->
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-if="renderedTemplate" class="text-sm text-[var(--text)]" v-html="renderedTemplate" />

      <!-- Default content -->
      <template v-else>
        <!-- Header -->
        <div class="flex items-start gap-2 mb-2">
          <span class="w-2 h-2 rounded-full mt-1 shrink-0" :class="stateColor" />
          <div class="min-w-0">
            <div class="font-semibold text-[var(--text)] text-sm leading-tight truncate">
              {{ displayName }}
            </div>
            <div class="text-xs text-[var(--text-muted)] mt-0.5">{{ object.type }}</div>
          </div>
        </div>

        <!-- State -->
        <div v-if="state" class="text-xs font-semibold mt-1" :class="stateTextColor">
          {{ state.state }}
        </div>

        <!-- Output -->
        <div
          v-if="state?.output"
          class="text-xs text-[var(--text-muted)] mt-2 leading-snug line-clamp-3 break-words"
        >
          {{ state.output }}
        </div>

        <!-- Badges -->
        <div
          v-if="state?.acknowledged || state?.in_downtime || state?.stale"
          class="flex gap-1.5 mt-2.5 flex-wrap"
        >
          <span
            v-if="state.acknowledged"
            class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-500/20 dark:bg-amber-500/15 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/40 dark:ring-amber-500/25"
          >
            <svg
              class="w-2.5 h-2.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="3"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            ACK
          </span>
          <span
            v-if="state.in_downtime"
            class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-500/20 dark:bg-blue-500/15 text-blue-700 dark:text-blue-400 ring-1 ring-blue-500/40 dark:ring-blue-500/25"
          >
            <svg class="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
            </svg>
            DOWNTIME
          </span>
          <span
            v-if="state.stale"
            class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-zinc-500/20 text-zinc-600 dark:text-zinc-400 ring-1 ring-zinc-500/40 dark:ring-zinc-500/25"
          >
            <svg
              class="w-2.5 h-2.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            STALE
          </span>
        </div>

        <!-- Sparkline trend chart -->
        <div v-if="sparkData.length > 1" class="mt-3 pt-2 border-t border-[var(--border)]">
          <div
            class="text-[10px] text-[var(--text-muted)] mb-1 uppercase tracking-wide font-medium"
          >
            Trend
          </div>
          <svg ref="sparkSvgRef" width="120" height="40" class="w-full" style="overflow: visible" />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import DOMPurify from 'dompurify';
import { computed, ref } from 'vue';

import { useSparkline } from '@/composables/useSparkline';
import { useStatesStore } from '@/stores/states';
import type { BoardObject, ObjectState } from '@/types/api';
import { interpolateTemplate } from '@/utils/template';

const _PURIFY_CONFIG = {
  ALLOWED_TAGS: ['b', 'i', 'u', 'em', 'strong', 'span', 'div', 'p', 'br', 'a', 'ul', 'ol', 'li'],
  ALLOWED_ATTR: ['href', 'class', 'style', 'target', 'rel'],
} as const satisfies DOMPurify.Config;

const props = defineProps<{
  object: BoardObject;
  state: ObjectState | undefined;
  x: number;
  y: number;
  template?: string | null;
}>();

const statesStore = useStatesStore();

const sparkSvgRef = ref<SVGSVGElement | null>(null);
const sparkData = computed(() => statesStore.history[props.object.id] ?? []);

useSparkline({ svgRef: sparkSvgRef, data: sparkData });

const renderedTemplate = computed(() => {
  if (!props.template) return null;
  const html = interpolateTemplate(props.template, props.object, props.state);
  return DOMPurify.sanitize(html, _PURIFY_CONFIG);
});

const displayName = computed(() => {
  if (props.object.label?.text) return props.object.label.text;
  if (props.object.host_name && props.object.service_description)
    return `${props.object.host_name} / ${props.object.service_description}`;
  return props.object.host_name ?? props.object.group_name ?? props.object.id;
});

const STATE_BG: Record<string, string> = {
  UP: 'bg-green-400',
  OK: 'bg-green-400',
  DOWN: 'bg-red-500',
  CRITICAL: 'bg-red-500',
  UNREACHABLE: 'bg-orange-400',
  UNKNOWN: 'bg-orange-400',
  WARNING: 'bg-warning',
  PENDING: 'bg-zinc-500',
};
const STATE_TEXT: Record<string, string> = {
  UP: 'text-green-600 dark:text-green-400',
  OK: 'text-green-600 dark:text-green-400',
  DOWN: 'text-red-600 dark:text-red-400',
  CRITICAL: 'text-red-600 dark:text-red-400',
  UNREACHABLE: 'text-orange-600 dark:text-orange-400',
  UNKNOWN: 'text-orange-600 dark:text-orange-400',
  WARNING: 'text-amber-600 dark:text-warning',
  PENDING: 'text-[var(--text-muted)]',
};

const stateColor = computed(() => STATE_BG[props.state?.state ?? 'PENDING'] ?? 'bg-zinc-500');
const stateTextColor = computed(
  () => STATE_TEXT[props.state?.state ?? 'PENDING'] ?? 'text-zinc-500',
);
</script>
