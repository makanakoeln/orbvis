<template>
    <div class="fixed z-50 pointer-events-none" :style="{ left: `${x}px`, top: `${y}px` }">
        <div
            class="bg-[var(--bg-glass)] backdrop-blur-md ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-xl p-3.5 min-w-52 max-w-72"
        >
            <!-- No permission: skip all templates and show only this -->
            <div v-if="isNoPermission" class="text-sm text-[var(--text-muted)] italic">
                {{ t('board.noPermission') }}
            </div>

            <!-- Custom template — sanitized via DOMPurify before rendering -->
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div
                v-else-if="renderedTemplate"
                class="text-sm text-[var(--text)]"
                v-html="renderedTemplate"
            />

            <!-- Default content -->
            <template v-else>
                <!-- Header -->
                <div class="flex items-start gap-2 mb-2">
                    <span
                        v-if="hasMonitoring"
                        class="w-2 h-2 rounded-full mt-1 shrink-0"
                        :class="stateColor"
                    />
                    <div class="min-w-0">
                        <div
                            class="font-semibold text-[var(--text)] text-sm leading-tight truncate"
                        >
                            {{ displayName }}
                        </div>
                        <div class="text-xs text-[var(--text-muted)] mt-0.5">
                            {{ hoverTypeLabel }}
                        </div>
                    </div>
                </div>

                <template v-if="hasMonitoring">
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

                    <!-- CMK Perfometer (loaded async from backend) -->
                    <div v-if="cmkPerfometer" class="mt-2.5 space-y-1">
                        <div class="text-[10px] font-medium text-[var(--text)] mb-1">
                            {{ cmkPerfometer.label }}
                        </div>
                        <div
                            v-for="(row, ri) in cmkPerfometer.rows"
                            :key="ri"
                            class="h-3 flex rounded overflow-hidden ring-1 ring-white/10"
                        >
                            <div
                                v-for="(seg, si) in row"
                                :key="si"
                                class="h-full transition-all"
                                :style="{ width: `${seg.pct}%`, backgroundColor: seg.color }"
                            />
                        </div>
                    </div>

                    <!-- Fallback: simple perf_data bars (shown while CMK perfometer loads or when no CMK backend) -->
                    <div v-else-if="perfMetrics.length" class="mt-2.5 space-y-1.5">
                        <template v-for="m in perfMetrics" :key="m.label">
                            <div class="flex justify-between items-baseline gap-1 text-[10px]">
                                <span class="text-[var(--text-muted)] truncate">{{ m.label }}</span>
                                <span class="text-[var(--text)] font-medium shrink-0">{{
                                    fmtMetricValue(m)
                                }}</span>
                            </div>
                            <div
                                v-if="utilPercent(m) > 0"
                                class="h-1.5 bg-[var(--bg-hover)] rounded-full overflow-hidden -mt-0.5"
                            >
                                <div
                                    class="h-full rounded-full"
                                    :style="{
                                        width: `${utilPercent(m)}%`,
                                        backgroundColor: utilColor(utilPercent(m)),
                                    }"
                                />
                            </div>
                        </template>
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
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M4.5 12.75l6 6 9-13.5"
                                />
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
                </template>
            </template>
        </div>
    </div>
</template>

<script setup lang="ts">
import DOMPurify, { type Config as DOMPurifyConfig } from 'dompurify';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { metricsApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import type { BoardObject, ObjectState, PerfometerResult } from '@/types/api';
import { getBoardObjectName, getObjectTypeLabel, VISUAL_ONLY_TYPES } from '@/utils/naming';
import { parsePerfData, type PerfMetric, utilColor, utilPercent } from '@/utils/perf';
import { interpolateTemplate } from '@/utils/template';

const _PURIFY_CONFIG = {
    ALLOWED_TAGS: ['b', 'i', 'u', 'em', 'strong', 'span', 'div', 'p', 'br', 'a', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'class', 'style', 'target', 'rel'],
} as const satisfies DOMPurifyConfig;

const props = defineProps<{
    object: BoardObject;
    state: ObjectState | undefined;
    x: number;
    y: number;
    template?: string | null;
    backendId?: string | null;
}>();

const { t } = useI18n();
const authStore = useAuthStore();

const cmkPerfometer = ref<PerfometerResult | null>(null);

onMounted(() => {
    // Perfometer only makes sense for an object linked to a specific service
    // (either a `service` object or a line/graph pointing at one).
    const isServiceLinked =
        props.object.type === 'service' ||
        ((props.object.type === 'line' || props.object.type === 'graph') &&
            !!props.object.service_description);
    if (
        isServiceLinked &&
        props.object.host_name &&
        props.object.service_description &&
        props.backendId &&
        authStore.accessToken
    ) {
        metricsApi
            .getPerfometer(
                props.backendId,
                props.object.host_name,
                props.object.service_description,
                authStore.accessToken,
            )
            .then((r) => {
                cmkPerfometer.value = r;
            })
            .catch(() => {});
    }
});

const renderedTemplate = computed(() => {
    if (!props.template) return null;
    const html = interpolateTemplate(props.template, props.object, props.state);
    return DOMPurify.sanitize(html, _PURIFY_CONFIG);
});

const displayName = computed(() => getBoardObjectName(props.object));

const hoverTypeLabel = computed(() => getObjectTypeLabel(props.object));

const hasMonitoring = computed(() => {
    // A line linked to a host/service is not purely decorative — show its state.
    if (props.object.type === 'line') {
        return !!(props.object.host_name || props.object.service_description);
    }
    return !(VISUAL_ONLY_TYPES as readonly string[]).includes(props.object.type);
});

const isNoPermission = computed(() => props.state?.state === 'NO_PERMISSION');

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

const perfMetrics = computed((): PerfMetric[] => {
    // Same reasoning as `isServiceLinked` above — only service-linked objects have perf data.
    const showPerf =
        props.object.type === 'service' ||
        ((props.object.type === 'line' || props.object.type === 'graph') &&
            !!props.object.service_description);
    if (!showPerf) return [];
    return parsePerfData(props.state?.perf_data ?? '').slice(0, 4);
});

function fmtMetricValue(m: PerfMetric): string {
    const v = Number.isInteger(m.value)
        ? String(m.value)
        : m.value.toFixed(2).replace(/\.?0+$/, '');
    return `${v}${m.unit}`;
}
</script>
