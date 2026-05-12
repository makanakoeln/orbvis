<template>
    <div ref="rootEl" class="fixed z-50 pointer-events-none" :style="positionStyle">
        <div
            class="bg-[var(--bg-glass)] backdrop-blur-md ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-xl p-3.5 min-w-52 max-w-72"
        >
            <!-- No permission: skip all templates and show only this -->
            <div v-if="isNoPermission" class="text-sm text-[var(--text-muted)] italic">
                {{ t('board.noPermission') }}
            </div>

            <!-- NOT_FOUND: object referenced on the board doesn't exist in monitoring data. -->
            <div v-else-if="isNotFound" class="text-sm text-[var(--text-muted)] italic">
                <div class="font-semibold text-[var(--text)] not-italic mb-1">
                    {{ displayName }}
                </div>
                {{ t('board.notFound') }}
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
                <!-- Header: hostname + state on one line — operator reads
                     "localhost — UP since 2d 11h" as a single headline. -->
                <div class="flex items-baseline gap-2 flex-wrap">
                    <span
                        v-if="hasMonitoring"
                        class="w-2 h-2 rounded-full shrink-0 self-center"
                        :class="stateColor"
                    />
                    <div
                        class="font-semibold text-[var(--text)] text-sm leading-tight truncate min-w-0 flex-1"
                    >
                        {{ displayName }}
                    </div>
                    <span
                        v-if="hasMonitoring && state"
                        class="shrink-0 text-sm font-bold leading-tight"
                        :class="stateTextColor"
                    >
                        {{ state.state }}
                    </span>
                    <span
                        v-if="hasMonitoring && state && stateDuration"
                        class="shrink-0 text-[10px] text-[var(--text-muted)]"
                    >
                        {{ t('board.hover.since', { duration: stateDuration }) }}
                    </span>
                </div>
                <!-- Subtitle: type · alias · address · @site (full width, second row) -->
                <div class="text-xs text-[var(--text-muted)] mt-0.5 truncate">
                    {{ subtitleText }}
                </div>

                <template v-if="hasMonitoring">
                    <!-- Status modifiers (ACK / DOWNTIME / STALE / MUTED / Attempts) -->
                    <div v-if="state">
                        <!-- Attempts: only when interesting (SOFT escalation, attempt > 1) -->
                        <div v-if="attemptsBadge" class="text-[10px] mt-1.5" :class="attemptsCls">
                            {{ attemptsBadge }}
                        </div>
                        <!-- Modifier badges (ACK / DOWNTIME / STALE / MUTED) — directly
                             under the state so the operator sees "no action needed" or
                             "I won't be paged" before scrolling to output/pills. -->
                        <div
                            v-if="
                                state.acknowledged ||
                                state.in_downtime ||
                                state.stale ||
                                state.notifications_enabled === false
                            "
                            class="flex gap-1.5 mt-1.5 flex-wrap"
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
                                class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[var(--color-pending)]/20 text-[var(--text-muted)] dark:text-[var(--text-muted)] ring-1 ring-[var(--border)] dark:ring-[var(--border)]"
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
                            <!-- Critical operator awareness: notifications disabled means
                                 nobody gets paged when this host breaks. Don't let the
                                 operator assume otherwise. -->
                            <span
                                v-if="state.notifications_enabled === false"
                                class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-500/20 dark:bg-amber-500/15 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/40 dark:ring-amber-500/25"
                                :title="t('board.hover.notificationsDisabled')"
                            >
                                <svg
                                    class="w-2.5 h-2.5"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M9.143 17.082a24.248 24.248 0 003.844.148m-3.844-.148a23.856 23.856 0 01-5.455-1.31 8.964 8.964 0 002.3-5.542m3.155 6.852a3 3 0 005.667 1.97m1.965-2.277L21 21M4.5 4.5l15 15"
                                    />
                                </svg>
                                MUTED
                            </span>
                        </div>
                    </div>

                    <!-- Output -->
                    <div
                        v-if="state?.output"
                        class="text-xs text-[var(--text-muted)] mt-2.5 leading-snug line-clamp-3 break-words"
                    >
                        {{ state.output }}
                    </div>

                    <!-- Services summary pills (host objects only) -->
                    <div v-if="servicePills.length" class="flex flex-wrap gap-1 mt-2.5">
                        <span
                            v-for="pill in servicePills"
                            :key="pill.label"
                            class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                            :class="pill.cls"
                        >
                            <span class="w-1.5 h-1.5 rounded-full" :class="pill.dot" />
                            {{ pill.count }} {{ pill.label }}
                        </span>
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

                    <!-- Fallback: simple perf_data bars — only when no CMK perfometer is on the way -->
                    <div
                        v-else-if="cmkPerfometerStatus !== 'loading' && perfMetrics.length"
                        class="mt-2.5 space-y-1.5"
                    >
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

                    <!-- Next check (relative; warns when overdue) -->
                    <div v-if="nextCheckText" class="text-[10px] mt-2.5" :class="nextCheckText.cls">
                        {{ nextCheckText.text }}
                    </div>
                </template>
            </template>
        </div>
    </div>
</template>

<script setup lang="ts">
import DOMPurify, { type Config as DOMPurifyConfig } from 'dompurify';
import { computed, type CSSProperties, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { metricsApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import type { BoardObject, ObjectState, PerfometerResult } from '@/types/api';
import { getBoardObjectIdentifier, getObjectTypeLabel, VISUAL_ONLY_TYPES } from '@/utils/naming';
import { parsePerfData, type PerfMetric, utilColor, utilPercent } from '@/utils/perf';
import { interpolateTemplate } from '@/utils/template';
import { formatRelativeDuration, formatRelativeFuture } from '@/utils/time';

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
    connectionId?: string | null;
    // Bounding rect of the hovered icon (in viewport coords). When the tooltip
    // has to flip to avoid overflow we anchor the flipped position at this
    // rect's edges so the tooltip never lands on top of the icon.
    anchorRect?: { left: number; top: number; right: number; bottom: number } | null;
}>();

const { t } = useI18n();
const authStore = useAuthStore();

const cmkPerfometer = ref<PerfometerResult | null>(null);
// Tracks whether a /metrics/perfometer fetch is in flight, so we can hide the
// raw perf_data fallback while the proper CMK perfometer is still loading —
// otherwise the tooltip flickers between two different bar styles.
const cmkPerfometerStatus = ref<'idle' | 'loading' | 'done'>('idle');

// Viewport-aware positioning: render once invisible to measure, then flip to
// the cursor's left/top side if the tooltip would overflow the right/bottom
// edge of the viewport. Recomputes on prop changes so the same instance can
// follow the cursor across objects without sticking off-screen.
const rootEl = ref<HTMLDivElement | null>(null);
const adjusted = ref<{ left: number; top: number; ready: boolean }>({
    left: props.x,
    top: props.y,
    ready: false,
});

const positionStyle = computed<CSSProperties>(() => ({
    left: `${adjusted.value.left}px`,
    top: `${adjusted.value.top}px`,
    visibility: adjusted.value.ready ? 'visible' : 'hidden',
}));

// Effective viewport bounds in *this window's* coordinate system. When OrbVis
// runs inside Checkmk's <iframe name="main">, the outer browser window is
// often smaller than the iframe's own innerHeight, so a position that fits
// `window.innerHeight` can still paint past the visible parent edge. Read the
// top window's size when same-origin allows it, and translate it back into
// our local coords via the iframe's offset.
function getEffectiveBounds(): { width: number; height: number } {
    const fallback = { width: window.innerWidth, height: window.innerHeight };
    if (window === window.top) return fallback;
    try {
        const top = window.top;
        const frame = window.frameElement as HTMLIFrameElement | null;
        if (!top || !frame) return fallback;
        const fr = frame.getBoundingClientRect();
        return {
            width: Math.min(fallback.width, top.innerWidth - fr.left),
            height: Math.min(fallback.height, top.innerHeight - fr.top),
        };
    } catch {
        return fallback;
    }
}

async function updatePosition() {
    await nextTick();
    if (!rootEl.value) return;
    const rect = rootEl.value.getBoundingClientRect();
    const { width: viewportW, height: viewportH } = getEffectiveBounds();
    const margin = 8;
    const gap = 8;
    let left = props.x;
    let top = props.y;
    if (left + rect.width > viewportW - margin) {
        // Flip past the icon's *left edge* if we know it; otherwise back off
        // from the cursor by the tooltip width. Cursor-based fallback can
        // overlap a small icon, so anchorRect is strongly preferred.
        const flipFrom = props.anchorRect ? props.anchorRect.left : props.x;
        left = Math.max(margin, flipFrom - rect.width - gap);
    }
    if (top + rect.height > viewportH - margin) {
        const flipFrom = props.anchorRect ? props.anchorRect.top : props.y;
        top = Math.max(margin, flipFrom - rect.height - gap);
    }
    adjusted.value = { left, top, ready: true };
}

watch(
    () => [props.x, props.y],
    () => {
        adjusted.value.ready = false;
        void updatePosition();
    },
);

onMounted(() => {
    void updatePosition();
});

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
        props.connectionId &&
        authStore.accessToken &&
        // No perfdata to fetch when the service doesn't exist or we're locked out.
        props.state?.state !== 'NOT_FOUND' &&
        props.state?.state !== 'NO_PERMISSION'
    ) {
        cmkPerfometerStatus.value = 'loading';
        metricsApi
            .getPerfometer(
                props.connectionId,
                props.object.host_name,
                props.object.service_description,
                authStore.accessToken,
            )
            .then((r) => {
                cmkPerfometer.value = r;
            })
            .catch(() => {})
            .finally(() => {
                cmkPerfometerStatus.value = 'done';
            });
    }
});

const renderedTemplate = computed(() => {
    if (!props.template) return null;
    const html = interpolateTemplate(props.template, props.object, props.state);
    return DOMPurify.sanitize(html, _PURIFY_CONFIG);
});

const displayName = computed(() => getBoardObjectIdentifier(props.object));

const hoverTypeLabel = computed(() => getObjectTypeLabel(props.object));

const hasMonitoring = computed(() => {
    // A line linked to a host/service is not purely decorative — show its state.
    if (props.object.type === 'line') {
        return !!(props.object.host_name || props.object.service_description);
    }
    return !(VISUAL_ONLY_TYPES as readonly string[]).includes(props.object.type);
});

const isNoPermission = computed(() => props.state?.state === 'NO_PERMISSION');
const isNotFound = computed(() => props.state?.state === 'NOT_FOUND');

const STATE_BG: Record<string, string> = {
    UP: 'bg-green-400',
    OK: 'bg-green-400',
    DOWN: 'bg-red-500',
    CRITICAL: 'bg-red-500',
    UNREACHABLE: 'bg-orange-400',
    UNKNOWN: 'bg-orange-400',
    WARNING: 'bg-warning',
    PENDING: 'bg-[var(--color-pending)]',
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

const stateColor = computed(
    () => STATE_BG[props.state?.state ?? 'PENDING'] ?? 'bg-[var(--color-pending)]',
);
const stateTextColor = computed(
    () => STATE_TEXT[props.state?.state ?? 'PENDING'] ?? 'text-[var(--text-muted)]',
);

const subtitleText = computed(() => {
    const parts: string[] = [hoverTypeLabel.value];
    const seen = new Set<string>([displayName.value]);
    const push = (raw: string | undefined | null, prefix = '') => {
        const v = raw?.trim();
        if (!v || seen.has(v)) return;
        seen.add(v);
        parts.push(prefix ? `${prefix}${v}` : v);
    };
    // alias and address help identify the host beyond the (possibly customised)
    // displayName; site is shown last as a "@site" suffix so it reads naturally
    // ("host · 10.0.4.12 · @eu_west").
    push(props.state?.alias);
    push(props.state?.address);
    push(props.state?.site_id, '@');
    return parts.join(' · ');
});

// Reactive clock so "since X" / "next check in X" tick down while the tooltip
// stays open. Driven by a 1-Hz interval that lives only as long as the
// component is mounted, so closed tooltips don't keep timers alive.
const nowMs = ref(Date.now());
let _tick: ReturnType<typeof setInterval> | null = null;
onMounted(() => {
    _tick = setInterval(() => {
        nowMs.value = Date.now();
    }, 1000);
});
onUnmounted(() => {
    if (_tick) clearInterval(_tick);
    _tick = null;
});

const attemptsBadge = computed(() => {
    const cur = props.state?.current_attempt ?? 0;
    const max = props.state?.max_attempts ?? 0;
    if (!cur || !max) return '';
    // Steady-state HARD checks don't need to advertise "1/3" — show only when
    // there's something interesting (SOFT progression or non-first attempt).
    if (props.state?.state_type === 'SOFT' || cur > 1) {
        return `${props.state?.state_type ?? ''} ${cur}/${max}`.trim();
    }
    return '';
});

const stateDuration = computed(() =>
    formatRelativeDuration(props.state?.last_state_change, nowMs.value),
);

// SOFT-state escalation deserves an amber attention cue; HARD steady-state is
// rendered muted (or hidden entirely by attemptsBadge's own gate).
const attemptsCls = computed(() =>
    props.state?.state_type === 'SOFT'
        ? 'text-amber-600 dark:text-amber-400 font-semibold'
        : 'text-[var(--text-muted)]',
);

interface NextCheckText {
    text: string;
    cls: string;
}
// CMC's check scheduling can make `next_check` lag behind "now" by a
// second or two even when the check is healthy. Suppress the "overdue"
// label until the LAST check is itself stale by this many seconds.
const OVERDUE_GRACE_SECONDS = 60;
const nextCheckText = computed((): NextCheckText | null => {
    const ts = props.state?.next_check;
    if (!ts) return null;
    const future = formatRelativeFuture(ts, nowMs.value);
    if (future) {
        return {
            text: t('board.hover.nextCheckIn', { duration: future }),
            cls: 'text-[var(--text-muted)]',
        };
    }
    // next_check is in the past. CMC schedules checks sub-second and
    // returns a `next_check` value that's already a hair behind "now"
    // even immediately after a successful check — flashing "overdue"
    // every render would be wrong. Only treat the check as overdue if
    // the LAST one is also stale; otherwise show the freshness via
    // last_check.
    const lastCheck = props.state?.last_check;
    const sinceLastCheckSec =
        lastCheck && lastCheck > 0 ? Math.floor(nowMs.value / 1000 - lastCheck) : Infinity;
    if (sinceLastCheckSec < OVERDUE_GRACE_SECONDS) {
        return null;
    }
    const overdue = formatRelativeDuration(ts, nowMs.value);
    if (!overdue) return null;
    return {
        text: t('board.hover.checkOverdue', { duration: overdue }),
        cls: 'text-amber-600 dark:text-amber-400',
    };
});

interface ServicePill {
    label: 'OK' | 'WARN' | 'CRIT' | 'UNKN' | 'PEND';
    count: number;
    cls: string;
    dot: string;
}

const servicePills = computed((): ServicePill[] => {
    // Hosts: per-host service-state breakdown.
    // Hostgroups/Servicegroups: per-member state breakdown — the backend
    // populates the same ``services_summary`` shape (UP→ok, DOWN→critical,
    // UNREACHABLE→unknown for hostgroups), so the same pill row works.
    if (
        props.object.type !== 'host' &&
        props.object.type !== 'hostgroup' &&
        props.object.type !== 'servicegroup'
    )
        return [];
    const summary = props.state?.services_summary;
    if (!summary) return [];
    // Severity-descending: a CRIT pill catches the eye before "all green",
    // matching the operator's "what's broken?" mental model. OK is still
    // shown last as confirmation.
    const pills: ServicePill[] = [];
    if (summary.critical) {
        pills.push({
            label: 'CRIT',
            count: summary.critical,
            cls: 'bg-red-500/15 text-red-700 dark:text-red-400 ring-1 ring-red-500/30',
            dot: 'bg-red-500',
        });
    }
    if (summary.unknown) {
        pills.push({
            label: 'UNKN',
            count: summary.unknown,
            cls: 'bg-orange-500/15 text-orange-700 dark:text-orange-400 ring-1 ring-orange-500/30',
            dot: 'bg-orange-400',
        });
    }
    if (summary.warning) {
        pills.push({
            label: 'WARN',
            count: summary.warning,
            cls: 'bg-amber-500/15 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/30',
            dot: 'bg-warning',
        });
    }
    if (summary.pending) {
        pills.push({
            label: 'PEND',
            count: summary.pending,
            cls: 'bg-[var(--color-pending)]/15 text-[var(--text-muted)] dark:text-[var(--text-muted)] ring-1 ring-[var(--border)]',
            dot: 'bg-[var(--color-pending)]',
        });
    }
    if (summary.ok) {
        pills.push({
            label: 'OK',
            count: summary.ok,
            cls: 'bg-green-500/15 text-green-700 dark:text-green-400 ring-1 ring-green-500/30',
            dot: 'bg-green-500',
        });
    }
    return pills;
});

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
