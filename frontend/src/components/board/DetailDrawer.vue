<template>
    <CmkSlideIn
        :open="!!object"
        size="narrow"
        :modal="false"
        border-color="none"
        :aria-label="displayName"
        :portal-to="portalTarget"
        @close="emit('close')"
    >
        <div
            v-if="object"
            class="detail-drawer"
            :class="`detail-drawer--${severityKind}`"
            @click.stop
        >
            <div
                class="detail-drawer__severity-bar"
                :style="{ background: state ? stateColor(state.state) : 'var(--border)' }"
            />

            <header class="detail-drawer__header">
                <div class="detail-drawer__title">
                    <div class="detail-drawer__title-row">
                        <span class="detail-drawer__name" :title="displayName">{{
                            displayName
                        }}</span>
                        <span class="detail-drawer__type-pill">{{ typeLabel }}</span>
                    </div>
                    <div v-if="state" class="detail-drawer__state-line">
                        <span
                            class="detail-drawer__state-pill"
                            :style="{
                                color: stateColor(state.state),
                                borderColor: stateColor(state.state),
                                background: stateBgColor(state.state),
                            }"
                        >
                            {{ state.state }}
                        </span>
                        <span v-if="sinceText" class="detail-drawer__since-text">{{
                            sinceText
                        }}</span>
                    </div>
                </div>
                <a
                    v-if="checkmkUrlFull"
                    :href="checkmkUrlFull"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="detail-drawer__icon-btn"
                    :title="t('board.detailDrawer.openInCheckmk')"
                    :aria-label="t('board.detailDrawer.openInCheckmk')"
                >
                    <CmkIcon name="export-link" size="small" />
                </a>
                <button
                    type="button"
                    class="detail-drawer__close"
                    :title="t('board.detailDrawer.close')"
                    @click="emit('close')"
                >
                    ×
                </button>
            </header>

            <div v-if="state" class="detail-drawer__body">
                <CmkTabs v-model="activeTab" class="detail-drawer__tabs">
                    <template #tabs>
                        <CmkTab id="status">{{ t('board.detailDrawer.tabStatus') }}</CmkTab>
                        <CmkTab v-if="showPerformanceTab" id="performance">{{
                            t('board.detailDrawer.tabPerformance')
                        }}</CmkTab>
                        <CmkTab v-if="showContextTab" id="context">{{
                            t('board.detailDrawer.tabContext')
                        }}</CmkTab>
                        <CmkTab v-if="showActivityTab" id="activity">
                            <span class="detail-drawer__tab-with-count">
                                {{ t('board.detailDrawer.tabActivity') }}
                                <span class="detail-drawer__tab-count">{{
                                    commentList.length + downtimeList.length
                                }}</span>
                            </span>
                        </CmkTab>
                    </template>

                    <template #tab-contents>
                        <CmkTabContent id="status" spacing="none">
                            <div class="detail-drawer__pane">
                                <div v-if="modifiers.length" class="detail-drawer__badges">
                                    <span
                                        v-for="mod in modifiers"
                                        :key="mod.label"
                                        class="detail-drawer__badge"
                                        :class="`detail-drawer__badge--${mod.kind}`"
                                    >
                                        {{ mod.label }}
                                    </span>
                                </div>

                                <pre v-if="state.output" class="detail-drawer__output">{{
                                    state.output
                                }}</pre>

                                <div
                                    v-if="serviceChips.length"
                                    class="detail-drawer__chips"
                                    :style="{
                                        gridTemplateColumns: `repeat(${serviceChips.length}, 1fr)`,
                                    }"
                                >
                                    <component
                                        :is="chip.url ? 'a' : 'button'"
                                        v-for="chip in serviceChips"
                                        :key="chip.state"
                                        :type="chip.url ? undefined : 'button'"
                                        :href="chip.url || undefined"
                                        :target="chip.url ? '_blank' : undefined"
                                        :rel="chip.url ? 'noopener noreferrer' : undefined"
                                        class="detail-drawer__chip"
                                        :class="
                                            chip.count > 0
                                                ? `detail-drawer__chip--${chip.tone}`
                                                : 'detail-drawer__chip--zero'
                                        "
                                        :disabled="chip.count === 0 || !chip.url ? true : undefined"
                                    >
                                        <span class="detail-drawer__chip-count">{{
                                            chip.count
                                        }}</span>
                                        <span class="detail-drawer__chip-label">{{
                                            chip.label
                                        }}</span>
                                    </component>
                                </div>

                                <div
                                    v-if="hostChips.length"
                                    class="detail-drawer__chips"
                                    :style="{
                                        gridTemplateColumns: `repeat(${hostChips.length}, 1fr)`,
                                    }"
                                >
                                    <component
                                        :is="chip.url ? 'a' : 'button'"
                                        v-for="chip in hostChips"
                                        :key="chip.state"
                                        :type="chip.url ? undefined : 'button'"
                                        :href="chip.url || undefined"
                                        :target="chip.url ? '_blank' : undefined"
                                        :rel="chip.url ? 'noopener noreferrer' : undefined"
                                        class="detail-drawer__chip"
                                        :class="
                                            chip.count > 0
                                                ? `detail-drawer__chip--${chip.tone}`
                                                : 'detail-drawer__chip--zero'
                                        "
                                        :disabled="chip.count === 0 || !chip.url ? true : undefined"
                                    >
                                        <span class="detail-drawer__chip-count">{{
                                            chip.count
                                        }}</span>
                                        <span class="detail-drawer__chip-label">{{
                                            chip.label
                                        }}</span>
                                    </component>
                                </div>

                                <dl
                                    v-if="metaRows.length || checkInfoRows.length"
                                    class="detail-drawer__meta"
                                >
                                    <template v-for="row in metaRows" :key="row.label">
                                        <dt>{{ row.label }}</dt>
                                        <dd>{{ row.value }}</dd>
                                    </template>
                                    <template v-for="row in checkInfoRows" :key="row.label">
                                        <dt>{{ row.label }}</dt>
                                        <dd
                                            :class="
                                                row.tone
                                                    ? `detail-drawer__meta-value--${row.tone}`
                                                    : ''
                                            "
                                        >
                                            {{ row.value }}
                                        </dd>
                                    </template>
                                </dl>
                            </div>
                        </CmkTabContent>

                        <CmkTabContent v-if="showPerformanceTab" id="performance" spacing="none">
                            <div class="detail-drawer__pane">
                                <div v-if="mainHeadline" class="detail-drawer__main-metric">
                                    <div class="detail-drawer__main-metric-head">
                                        <span class="detail-drawer__main-metric-label">{{
                                            mainHeadline.label
                                        }}</span>
                                    </div>
                                    <div
                                        class="detail-drawer__perf-bar-wrap detail-drawer__perf-bar-wrap--lg"
                                    >
                                        <div
                                            class="detail-drawer__perf-bar"
                                            :style="{
                                                width: mainHeadline.pct + '%',
                                                background: mainHeadline.color,
                                            }"
                                        />
                                        <div
                                            v-if="mainPerfRow?.warnPct !== null && mainPerfRow"
                                            class="detail-drawer__perf-mark detail-drawer__perf-mark--warn"
                                            :style="{ left: mainPerfRow.warnPct + '%' }"
                                            :title="`warn: ${mainPerfRow.warnLabel}`"
                                        />
                                        <div
                                            v-if="mainPerfRow?.critPct !== null && mainPerfRow"
                                            class="detail-drawer__perf-mark detail-drawer__perf-mark--crit"
                                            :style="{ left: mainPerfRow.critPct + '%' }"
                                            :title="`crit: ${mainPerfRow.critLabel}`"
                                        />
                                    </div>
                                    <div
                                        v-if="mainHeadline.valueLabel"
                                        class="detail-drawer__main-metric-value"
                                    >
                                        {{ mainHeadline.valueLabel }}
                                    </div>
                                </div>

                                <div v-if="mainHistoryKey" class="detail-drawer__chart-wrap">
                                    <MetricChart
                                        :data="historyData"
                                        :metric-keys="[mainHistoryKey]"
                                        :window-secs="HISTORY_MINUTES * 60"
                                        :thresholds="mainThresholds"
                                        :unit="mainMetric?.unit"
                                        :dark="isDark"
                                    />
                                </div>

                                <div
                                    v-if="longOutputRows.length"
                                    class="detail-drawer__pane-section"
                                >
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.details') }}
                                    </div>
                                    <dl class="detail-drawer__output-rows">
                                        <template v-for="(row, i) in longOutputRows" :key="i">
                                            <dt v-if="row.label">{{ row.label }}</dt>
                                            <dd>{{ row.value }}</dd>
                                        </template>
                                    </dl>
                                </div>

                                <details
                                    v-if="otherPerfRows.length"
                                    class="detail-drawer__raw-metrics"
                                >
                                    <summary>
                                        {{
                                            t('board.detailDrawer.rawMetrics', {
                                                n: otherPerfRows.length,
                                            })
                                        }}
                                    </summary>
                                    <div class="detail-drawer__perf">
                                        <div
                                            v-for="row in otherPerfRows"
                                            :key="row.label"
                                            class="detail-drawer__perf-row"
                                        >
                                            <div
                                                class="detail-drawer__perf-label"
                                                :title="row.label"
                                            >
                                                {{ row.label }}
                                            </div>
                                            <div class="detail-drawer__perf-bar-wrap">
                                                <div
                                                    class="detail-drawer__perf-bar"
                                                    :style="{
                                                        width: row.pct + '%',
                                                        background: row.color,
                                                    }"
                                                />
                                                <div
                                                    v-if="row.warnPct !== null"
                                                    class="detail-drawer__perf-mark detail-drawer__perf-mark--warn"
                                                    :style="{ left: row.warnPct + '%' }"
                                                    :title="`warn: ${row.warnLabel}`"
                                                />
                                                <div
                                                    v-if="row.critPct !== null"
                                                    class="detail-drawer__perf-mark detail-drawer__perf-mark--crit"
                                                    :style="{ left: row.critPct + '%' }"
                                                    :title="`crit: ${row.critLabel}`"
                                                />
                                            </div>
                                            <div class="detail-drawer__perf-value">
                                                {{ row.valueLabel }}
                                            </div>
                                        </div>
                                    </div>
                                </details>
                            </div>
                        </CmkTabContent>

                        <CmkTabContent v-if="showContextTab" id="context" spacing="none">
                            <div class="detail-drawer__pane">
                                <dl
                                    v-if="contextMetaRowsWithoutCheckCmd.length"
                                    class="detail-drawer__meta"
                                >
                                    <template
                                        v-for="row in contextMetaRowsWithoutCheckCmd"
                                        :key="row.label"
                                    >
                                        <dt>{{ row.label }}</dt>
                                        <dd
                                            :class="
                                                row.tone
                                                    ? `detail-drawer__meta-value--${row.tone}`
                                                    : ''
                                            "
                                        >
                                            {{ row.value }}
                                        </dd>
                                    </template>
                                </dl>

                                <div v-if="checkCommandRow">
                                    <div class="detail-drawer__pane-heading">
                                        {{ checkCommandRow.label }}
                                    </div>
                                    <CmkCode :code-txt="checkCommandRow.value" width="fill" />
                                </div>

                                <dl
                                    v-if="topologyGroups.length"
                                    class="detail-drawer__meta detail-drawer__meta--stacked"
                                >
                                    <template v-for="group in topologyGroups" :key="group.label">
                                        <dt>{{ group.label }}</dt>
                                        <dd class="detail-drawer__chip-row">
                                            <CmkChip
                                                v-for="item in group.items"
                                                :key="item"
                                                size="small"
                                                :color="group.isHostList ? 'info' : 'others'"
                                                variant="outline"
                                                :as-div="!group.isHostList || !canSelectHost(item)"
                                                @click="
                                                    group.isHostList && canSelectHost(item)
                                                        ? emit('select-host', item)
                                                        : null
                                                "
                                            >
                                                {{ item }}
                                            </CmkChip>
                                        </dd>
                                    </template>
                                </dl>

                                <div v-if="labelEntries.length">
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.labels') }}
                                    </div>
                                    <div class="detail-drawer__chip-row">
                                        <CmkChip
                                            v-for="[key, value] in labelEntries"
                                            :key="key"
                                            size="small"
                                            color="others"
                                            variant="outline"
                                            as-div
                                            :title="`${key}: ${value}`"
                                        >
                                            <template #start>
                                                <span class="detail-drawer__label-key">{{
                                                    key
                                                }}</span>
                                            </template>
                                            {{ value }}
                                        </CmkChip>
                                    </div>
                                </div>
                            </div>
                        </CmkTabContent>

                        <CmkTabContent v-if="showActivityTab" id="activity" spacing="none">
                            <div class="detail-drawer__pane">
                                <div
                                    v-if="downtimeList.length"
                                    class="detail-drawer__pane-section detail-drawer__section--downtimes"
                                >
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.activeDowntimes') }}
                                    </div>
                                    <ul class="detail-drawer__list">
                                        <li
                                            v-for="dt in downtimeList"
                                            :key="dt.id"
                                            class="detail-drawer__list-row"
                                        >
                                            <div class="detail-drawer__list-meta">
                                                <span class="detail-drawer__list-author">{{
                                                    dt.author
                                                }}</span>
                                                <span
                                                    v-if="!dt.fixed"
                                                    class="detail-drawer__list-tag"
                                                    :title="
                                                        t('board.detailDrawer.flexibleDowntime')
                                                    "
                                                    >FLEX</span
                                                >
                                                <span class="detail-drawer__list-time">{{
                                                    dt.timeRange
                                                }}</span>
                                            </div>
                                            <div v-if="dt.comment" class="detail-drawer__list-text">
                                                {{ dt.comment }}
                                            </div>
                                        </li>
                                    </ul>
                                </div>

                                <div v-if="commentList.length" class="detail-drawer__pane-section">
                                    <div class="detail-drawer__pane-heading">
                                        {{ t('board.detailDrawer.comments') }}
                                    </div>
                                    <ul class="detail-drawer__list">
                                        <li
                                            v-for="c in commentList"
                                            :key="c.id"
                                            class="detail-drawer__list-row"
                                        >
                                            <div class="detail-drawer__list-meta">
                                                <span class="detail-drawer__list-author">{{
                                                    c.author
                                                }}</span>
                                                <span class="detail-drawer__list-time">{{
                                                    c.age
                                                }}</span>
                                                <span
                                                    v-if="c.expires"
                                                    class="detail-drawer__list-time"
                                                >
                                                    ·
                                                    {{ t('board.detailDrawer.expires') }}
                                                    {{ c.expires }}
                                                </span>
                                            </div>
                                            <div class="detail-drawer__list-text">
                                                {{ c.text }}
                                            </div>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </CmkTabContent>
                    </template>
                </CmkTabs>
            </div>

            <footer v-if="!isSite" class="detail-drawer__actions">
                <h4 class="detail-drawer__actions-title">
                    {{ t('board.detailDrawer.sectionActions') }}
                </h4>
                <div class="detail-drawer__actions-grid">
                    <CmkButton
                        v-if="!state?.acknowledged && isProblematic"
                        variant="success"
                        class="detail-drawer__action detail-drawer__action--primary"
                        @click="emit('acknowledge')"
                    >
                        {{ t('board.detailDrawer.ackLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-if="state?.acknowledged"
                        variant="warning"
                        class="detail-drawer__action"
                        @click="emit('remove-ack')"
                    >
                        {{ t('board.detailDrawer.removeAckLabel') }}
                    </CmkButton>
                    <CmkButton
                        variant="optional"
                        class="detail-drawer__action"
                        @click="emit('force-check')"
                    >
                        {{ t('board.detailDrawer.forceCheckLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-if="!state?.in_downtime"
                        variant="optional"
                        class="detail-drawer__action"
                        @click="emit('schedule-downtime')"
                    >
                        {{ t('board.detailDrawer.scheduleDowntimeLabel') }}
                    </CmkButton>
                    <CmkButton
                        v-if="state?.in_downtime"
                        variant="warning"
                        class="detail-drawer__action"
                        @click="emit('remove-downtime')"
                    >
                        {{ t('board.detailDrawer.removeDowntimeLabel') }}
                    </CmkButton>
                    <CmkButton
                        variant="optional"
                        class="detail-drawer__action"
                        @click="emit('add-comment')"
                    >
                        {{ t('board.detailDrawer.addCommentLabel') }}
                    </CmkButton>
                    <details class="detail-drawer__more">
                        <summary
                            class="detail-drawer__btn detail-drawer__btn--more"
                            :title="t('board.detailDrawer.moreActions')"
                        >
                            {{ t('board.detailDrawer.moreActions') }}
                        </summary>
                        <div class="detail-drawer__more-menu" role="menu">
                            <button
                                v-if="state?.notifications_enabled !== false"
                                type="button"
                                class="detail-drawer__more-item"
                                role="menuitem"
                                @click="
                                    closeMoreMenu($event);
                                    emit('disable-notifications');
                                "
                            >
                                {{ t('board.detailDrawer.disableNotificationsLabel') }}
                            </button>
                            <button
                                v-else
                                type="button"
                                class="detail-drawer__more-item"
                                role="menuitem"
                                @click="
                                    closeMoreMenu($event);
                                    emit('enable-notifications');
                                "
                            >
                                {{ t('board.detailDrawer.enableNotificationsLabel') }}
                            </button>
                        </div>
                    </details>
                </div>
            </footer>

            <footer v-else class="detail-drawer__actions detail-drawer__actions--site">
                <CmkButton
                    v-if="problemsUrlFull"
                    variant="success"
                    :href="problemsUrlFull"
                    target="_blank"
                    class="detail-drawer__action detail-drawer__action--primary"
                >
                    {{ t('board.detailDrawer.openProblems') }} ↗
                </CmkButton>
            </footer>
        </div>
    </CmkSlideIn>
</template>

<script setup lang="ts">
import { useMutationObserver } from '@vueuse/core';
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi, metricsApi } from '@/api/client';
import { fmtValueWithUnit } from '@/composables/useMetricChart';
import { useAuthStore } from '@/stores/auth';
import type {
    BoardObject,
    MetricPoint,
    ObjectDetails,
    ObjectState,
    PerfometerResult,
} from '@/types/api';
import { buildCheckmkUrl } from '@/utils/boardNavigation';
import { getBoardObjectName, getObjectTypeLabel } from '@/utils/naming';
import { parsePerfData, type PerfMetric, utilColor, utilPercent } from '@/utils/perf';
import { stateColor } from '@/utils/stateColors';
import { formatRelativeDuration, formatRelativeFuture } from '@/utils/time';
import CmkButton from '@/vendor/cmk/components/CmkButton.vue';
import { CmkChip } from '@/vendor/cmk/components/CmkChip';
import { CmkCode } from '@/vendor/cmk/components/CmkCode';
import CmkIcon from '@/vendor/cmk/components/CmkIcon';
import CmkSlideIn from '@/vendor/cmk/components/CmkSlideIn';
import { CmkTab, CmkTabContent, CmkTabs } from '@/vendor/cmk/components/CmkTabs';

import MetricChart from './MetricChart.vue';

function stateBgColor(state: string): string {
    const c = stateColor(state);
    if (c.startsWith('#') && c.length === 7) {
        const r = parseInt(c.slice(1, 3), 16);
        const g = parseInt(c.slice(3, 5), 16);
        const b = parseInt(c.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, 0.12)`;
    }
    return c;
}

const props = defineProps<{
    object: BoardObject | null;
    state?: ObjectState;
    checkmkUrl?: string | null;
    /** Board's connection_id — used to fetch on-demand object details. */
    connectionId?: string | null;
    /** CSS selector for the CmkSlideIn portal target. Defaults to body. */
    portalTarget?: string;
    /** Hostnames currently on the board — topology entries to those hosts
     * become clickable buttons that emit `select-host` for the parent to act on. */
    selectableHosts?: string[];
}>();

const portalTarget = computed(() => props.portalTarget);

const emit = defineEmits<{
    close: [];
    acknowledge: [];
    'remove-ack': [];
    'schedule-downtime': [];
    'remove-downtime': [];
    'force-check': [];
    'add-comment': [];
    'enable-notifications': [];
    'disable-notifications': [];
    /** Host name picked from the topology section — board may highlight + select it. */
    'select-host': [hostName: string];
}>();

const selectableHostSet = computed(() => new Set(props.selectableHosts ?? []));
function canSelectHost(host: string): boolean {
    return selectableHostSet.value.has(host);
}

// Drives age/overdue labels so they tick forward without a state push.
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

function closeMoreMenu(e: Event): void {
    const details = (e.currentTarget as HTMLElement).closest('details');
    if (details) (details as HTMLDetailsElement).open = false;
}

const auth = useAuthStore();

// On-demand details kept separate from the streamed ObjectState — long_output,
// comments, downtimes and topology rarely change but can be many KB each, so
// fetching them per Drawer-open keeps the WebSocket payload compact.
const details = ref<ObjectDetails | null>(null);
// CMK perf-o-meter result — same metric Checkmk shows in views, computed
// from the service's perfometer plugin definition (e.g. mem_used_percent for
// Linux Memory). Only populated for services.
const perfometer = ref<PerfometerResult | null>(null);

// Source the watch on primitive keys (not the reactive object) so it fires
// only when selection actually changes — state-stream updates that re-create
// the prop reference would otherwise cause refetches on every tick.
watch(
    [
        () => props.object?.type,
        () => props.object?.host_name,
        () => props.object?.service_description,
        () => props.connectionId,
    ],
    async ([objType, host, service, connId]) => {
        details.value = null;
        perfometer.value = null;
        if (!connId || !auth.accessToken || !host) return;
        if (objType !== 'host' && objType !== 'service') return;
        if (objType === 'service' && !service) return;
        const reqService = objType === 'service' ? (service ?? null) : null;
        try {
            const [detailsRes, perfRes] = await Promise.all([
                connectionsApi.objectDetails(connId, objType, host, reqService, auth.accessToken),
                objType === 'service' && reqService
                    ? metricsApi.getPerfometer(connId, host, reqService, auth.accessToken)
                    : Promise.resolve(null),
            ]);
            // Stale-response guard: between the await and now the user may have
            // clicked another object. Match all three identity fields so a host
            // response doesn't land on a same-named service or vice versa.
            // Note: service_description may be undefined on host BoardObjects
            // (Flow Board synthesises hosts without it) — normalise to null
            // before comparing so guard doesn't reject legitimate hosts.
            const currentService = props.object?.service_description ?? null;
            if (
                props.object?.type === objType &&
                props.object?.host_name === host &&
                currentService === reqService
            ) {
                details.value = detailsRes;
                perfometer.value = perfRes;
            }
        } catch {
            details.value = null;
            perfometer.value = null;
        }
    },
    { immediate: true },
);

const PROBLEM_STATES = new Set(['CRITICAL', 'WARNING', 'UNKNOWN', 'DOWN', 'UNREACHABLE']);
const isProblematic = computed(() => (props.state ? PROBLEM_STATES.has(props.state.state) : false));
const isSite = computed(() => props.object?.type === 'site');
const severityKind = computed(() => {
    const s = props.state?.state;
    if (!s) return 'pending';
    if (s === 'CRITICAL' || s === 'DOWN') return 'critical';
    if (s === 'UNREACHABLE') return 'unreachable';
    if (s === 'WARNING' || s === 'UNKNOWN') return 'warn';
    if (s === 'OK' || s === 'UP') return 'ok';
    return 'pending';
});

const { t } = useI18n();

const displayName = computed(() => (props.object ? getBoardObjectName(props.object) : ''));
const typeLabel = computed(() => (props.object ? getObjectTypeLabel(props.object) : ''));

const checkmkUrlFull = computed(() =>
    props.object ? buildCheckmkUrl(props.object, props.checkmkUrl ?? null) : null,
);

const problemsUrlFull = computed(() => {
    if (!props.object || props.object.type !== 'site' || !props.checkmkUrl) return null;
    const base = props.checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const siteId = props.object.host_name ?? props.state?.site_id;
    if (!siteId) return null;
    // svcproblems' built-in defaults (CRIT/WARN/UNKN active) are exactly what
    // the operator wants here — no filled_in, just the site scope.
    const params = new URLSearchParams({
        view_name: 'svcproblems',
        site: siteId,
    });
    return `${base}/check_mk/view.py?${params}`;
});

const sinceText = computed(() => {
    const duration = formatRelativeDuration(props.state?.last_state_change, nowMs.value);
    return duration ? t('board.detailDrawer.since', { duration }) : null;
});

interface SummaryChip {
    state: string;
    count: number;
    label: string;
    tone: 'crit' | 'warn' | 'unknown' | 'ok';
    url: string | null;
}

// Checkmk's filter machinery takes a single "svc_state" / "host_state" filter
// whose individual st*/hst* checkboxes are interpreted as a bitmask. A box
// only counts as ON when its parameter is present and equals "on" — sending
// "off" or omitting it both mean "exclude this state". The whole filter is
// only honored when "_active" lists svcstate/hoststate alongside the host /
// site filter; without it the Setup-defined view defaults win.
function svcStateOn(state: string): string {
    if (state === 'CRITICAL') return 'st2';
    if (state === 'WARNING') return 'st1';
    if (state === 'UNKNOWN') return 'st3';
    return 'st0'; // OK
}

function hostStateOn(state: string): string {
    if (state === 'DOWN') return 'hst1';
    if (state === 'UNREACHABLE') return 'hst2';
    return 'hst0'; // UP
}

function buildServiceChipUrl(state: string, count: number): string | null {
    if (count <= 0 || !props.checkmkUrl || !props.object) return null;
    const base = props.checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const params: Record<string, string> = {
        view_name: 'allservices',
        filled_in: 'filter',
        _active: 'svcstate;host',
        [svcStateOn(state)]: 'on',
    };
    if (props.object.type === 'site' && props.object.host_name) {
        params.site = props.object.host_name;
        params._active = 'svcstate;site';
    } else if (props.object.host_name) {
        params.host = props.object.host_name;
    } else {
        return null;
    }
    return `${base}/check_mk/view.py?${new URLSearchParams(params)}`;
}

function buildHostChipUrl(state: string, count: number): string | null {
    if (count <= 0 || !props.checkmkUrl || !props.object) return null;
    if (props.object.type !== 'site' || !props.object.host_name) return null;
    const base = props.checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    const params: Record<string, string> = {
        view_name: 'allhosts',
        filled_in: 'filter',
        _active: 'hoststate;site',
        site: props.object.host_name,
        [hostStateOn(state)]: 'on',
    };
    return `${base}/check_mk/view.py?${new URLSearchParams(params)}`;
}

const serviceChips = computed<SummaryChip[]>(() => {
    const s = props.state?.services_summary;
    if (!s) return [];
    const make = (
        state: string,
        count: number,
        label: string,
        tone: SummaryChip['tone'],
    ): SummaryChip => ({
        state,
        count,
        label,
        tone,
        url: buildServiceChipUrl(state, count),
    });
    // Hide problem chips at zero (visual noise); always keep the OK anchor so
    // the operator sees an "all green" cue when nothing is wrong.
    return [
        make('CRITICAL', s.critical ?? 0, 'CRIT', 'crit'),
        make('WARNING', s.warning ?? 0, 'WARN', 'warn'),
        make('UNKNOWN', s.unknown ?? 0, 'UNKN', 'unknown'),
        make('OK', s.ok ?? 0, 'OK', 'ok'),
    ].filter((chip) => chip.state === 'OK' || chip.count > 0);
});

// Site state output looks like "504 hosts (504 up, 0 down, 0 unreachable)";
// extract the host counts so we can render the same kind of chip row as services.
const hostsSummary = computed<{ up: number; down: number; unreachable: number } | null>(() => {
    if (!isSite.value) return null;
    const out = props.state?.output;
    if (!out) return null;
    const m = out.match(/(\d+)\s+up,\s*(\d+)\s+down,\s*(\d+)\s+unreachable/);
    if (!m) return null;
    return { up: parseInt(m[1], 10), down: parseInt(m[2], 10), unreachable: parseInt(m[3], 10) };
});

const hostChips = computed<SummaryChip[]>(() => {
    const h = hostsSummary.value;
    if (!h) return [];
    const make = (
        state: string,
        count: number,
        label: string,
        tone: SummaryChip['tone'],
    ): SummaryChip => ({
        state,
        count,
        label,
        tone,
        url: buildHostChipUrl(state, count),
    });
    return [
        make('DOWN', h.down, 'DOWN', 'crit'),
        make('UNREACHABLE', h.unreachable, 'UNRCH', 'warn'),
        make('UP', h.up, 'UP', 'ok'),
    ].filter((chip) => chip.state === 'UP' || chip.count > 0);
});

interface Modifier {
    label: string;
    kind: 'ack' | 'downtime' | 'stale' | 'muted' | 'flapping';
}
const modifiers = computed<Modifier[]>(() => {
    const s = props.state;
    if (!s) return [];
    const list: Modifier[] = [];
    if (s.acknowledged) list.push({ label: 'ACK', kind: 'ack' });
    if (s.in_downtime) list.push({ label: 'DOWNTIME', kind: 'downtime' });
    if (s.stale) list.push({ label: 'STALE', kind: 'stale' });
    if (s.notifications_enabled === false) list.push({ label: 'MUTED', kind: 'muted' });
    if (details.value?.is_flapping) list.push({ label: 'FLAPPING', kind: 'flapping' });
    return list;
});

const longOutputText = computed(() => details.value?.long_output ?? '');

interface MetaRow {
    label: string;
    value: string;
    tone?: 'warn';
}

const metaRows = computed<MetaRow[]>(() => {
    const s = props.state;
    const o = props.object;
    if (!s) return [];
    const rows: MetaRow[] = [];
    if (s.alias && s.alias !== displayName.value) {
        rows.push({ label: 'Alias', value: s.alias });
    }
    if (s.address) rows.push({ label: 'Address', value: s.address });
    if (o?.type === 'service' && o.host_name) {
        rows.push({ label: t('board.detailDrawer.host'), value: o.host_name });
    }
    // For site drawers, the site name is already the title — no point repeating it.
    if (s.site_id && o?.type !== 'site') {
        rows.push({ label: t('board.detailDrawer.site'), value: s.site_id });
    }
    return rows;
});

const checkInfoRows = computed<MetaRow[]>(() => {
    const s = props.state;
    if (!s) return [];
    const rows: MetaRow[] = [];
    const now = Math.floor(Date.now() / 1000);

    if (typeof s.current_attempt === 'number' && typeof s.max_attempts === 'number') {
        const isSoft = s.state_type === 'SOFT' || s.state_type === 'soft';
        rows.push({
            label: t('board.detailDrawer.attemptLabel'),
            value: t('board.detailDrawer.attemptValue', {
                current: s.current_attempt,
                max: s.max_attempts,
                type: isSoft
                    ? t('board.detailDrawer.stateTypeSoft')
                    : t('board.detailDrawer.stateTypeHard'),
            }),
            tone: isSoft ? 'warn' : undefined,
        });
    }

    if (s.last_check && s.last_check > 0) {
        rows.push({
            label: t('board.detailDrawer.lastCheck'),
            value: t('board.detailDrawer.timeAgo', {
                duration: formatRelativeDuration(s.last_check, nowMs.value),
            }),
        });
    } else if (s.last_check === 0) {
        rows.push({
            label: t('board.detailDrawer.lastCheck'),
            value: t('board.detailDrawer.never'),
        });
    }

    if (s.next_check && s.next_check > 0) {
        if (s.next_check < now) {
            rows.push({
                label: t('board.detailDrawer.nextCheck'),
                value: `${t('board.detailDrawer.overdue')} (${formatRelativeDuration(s.next_check, nowMs.value)})`,
                tone: 'warn',
            });
        } else {
            rows.push({
                label: t('board.detailDrawer.nextCheck'),
                value: t('board.detailDrawer.timeIn', {
                    duration: formatRelativeFuture(s.next_check, nowMs.value),
                }),
            });
        }
    }

    const d = details.value;
    // Service-only: when did this check last go OK? Lets the operator see
    // "broken for 2 days" vs. "just flipped" without leaving the drawer.
    if (d?.last_time_ok && d.last_time_ok > 0 && s.state !== 'OK') {
        rows.push({
            label: t('board.detailDrawer.lastOk'),
            value: t('board.detailDrawer.timeAgo', {
                duration: formatRelativeDuration(d.last_time_ok, nowMs.value),
            }),
        });
    }

    return rows;
});

// Topology / membership / labels — from on-demand details. Empty groups are
// hidden so the drawer stays compact when nothing useful is set.
interface TopologyGroup {
    label: string;
    items: string[];
    /** Optional Checkmk-style hostname links (parents, children) */
    isHostList?: boolean;
}
const topologyGroups = computed<TopologyGroup[]>(() => {
    const d = details.value;
    if (!d) return [];
    const out: TopologyGroup[] = [];
    if (d.parents.length)
        out.push({ label: t('board.detailDrawer.parents'), items: d.parents, isHostList: true });
    if (d.children.length)
        out.push({ label: t('board.detailDrawer.children'), items: d.children, isHostList: true });
    if (d.host_groups.length)
        out.push({ label: t('board.detailDrawer.hostGroups'), items: d.host_groups });
    if (d.service_groups.length)
        out.push({ label: t('board.detailDrawer.serviceGroups'), items: d.service_groups });
    if (d.contact_groups.length)
        out.push({ label: t('board.detailDrawer.contactGroups'), items: d.contact_groups });
    return out;
});

const labelEntries = computed(() => Object.entries(details.value?.labels ?? {}));

interface Comment {
    id: number;
    author: string;
    text: string;
    age: string;
    expires: string | null;
}
const commentList = computed<Comment[]>(() => {
    const list = details.value?.comments ?? [];
    return list.map((c) => ({
        id: c.id,
        author: c.author || '?',
        text: c.comment,
        age: t('board.detailDrawer.timeAgo', {
            duration: formatRelativeDuration(c.entry_time, nowMs.value),
        }),
        expires:
            c.expire_time && c.expire_time > 0
                ? t('board.detailDrawer.timeIn', {
                      duration: formatRelativeFuture(c.expire_time, nowMs.value),
                  })
                : null,
    }));
});

interface Downtime {
    id: number;
    author: string;
    comment: string;
    timeRange: string;
    fixed: boolean;
}
function fmtDateTime(ts: number): string {
    return new Date(ts * 1000).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}
const downtimeList = computed<Downtime[]>(() => {
    const list = details.value?.downtimes ?? [];
    return list.map((d) => ({
        id: d.id,
        author: d.author || '?',
        comment: d.comment,
        timeRange: `${fmtDateTime(d.start_time)} → ${fmtDateTime(d.end_time)}`,
        fixed: d.fixed,
    }));
});

interface PerfRow {
    label: string;
    pct: number;
    color: string;
    warnPct: number | null;
    critPct: number | null;
    warnLabel: string;
    critLabel: string;
    valueLabel: string;
}

function fmtNum(n: number, unit: string): string {
    return fmtValueWithUnit(n, unit);
}

// Tab visibility — only show tabs that actually have content. The Status tab
// always renders (output + state badges + chips); others appear conditionally.
const showPerformanceTab = computed(() => perfRows.value.length > 0 || !!longOutputText.value);
const showContextTab = computed(
    () =>
        topologyGroups.value.length > 0 ||
        labelEntries.value.length > 0 ||
        contextMetaRows.value.length > 0,
);
const showActivityTab = computed(
    () => commentList.value.length > 0 || downtimeList.value.length > 0,
);

const activeTab = ref('status');

watch([() => props.object?.host_name, () => props.object?.service_description], () => {
    // Reset to overview whenever the user picks a different object so they
    // don't land on an empty tab from the previous selection.
    activeTab.value = 'status';
});

interface MetaRow2 {
    label: string;
    value: string;
    tone?: 'warn';
}

const contextMetaRows = computed<MetaRow2[]>(() => {
    const d = details.value;
    const rows: MetaRow2[] = [];
    if (!d) return rows;
    if (d.check_command)
        rows.push({ label: t('board.detailDrawer.checkCommand'), value: d.check_command });
    if (typeof d.latency === 'number' && d.latency >= 0) {
        rows.push({
            label: t('board.detailDrawer.latency'),
            value: `${(d.latency * 1000).toFixed(0)} ms`,
        });
    }
    if (d.notification_period && d.notification_period !== '24X7') {
        rows.push({
            label: t('board.detailDrawer.notificationPeriod'),
            value: d.notification_period,
            tone: d.in_notification_period ? undefined : 'warn',
        });
    }
    return rows;
});

// Check command gets its own CmkCode block — it's typically long and benefits
// from monospace + horizontal scroll, while latency / notif. period stay in
// the regular dt/dd grid.
const checkCommandRow = computed<MetaRow2 | null>(
    () =>
        contextMetaRows.value.find((r) => r.label === t('board.detailDrawer.checkCommand')) ?? null,
);
const contextMetaRowsWithoutCheckCmd = computed<MetaRow2[]>(() =>
    contextMetaRows.value.filter((r) => r.label !== t('board.detailDrawer.checkCommand')),
);

const parsedMetrics = computed<PerfMetric[]>(() => {
    const raw = props.state?.perf_data;
    return raw ? parsePerfData(raw) : [];
});

function _displayLabel(metricId: string): string {
    return details.value?.metric_titles[metricId] || metricId;
}

function _toPerfRow(m: PerfMetric): PerfRow {
    const pct = utilPercent(m);
    const refMax = m.max ?? m.crit ?? null;
    const warnPct =
        m.warn !== null && refMax !== null && refMax > 0
            ? Math.min(100, (m.warn / refMax) * 100)
            : null;
    const critPct =
        m.crit !== null && refMax !== null && refMax > 0
            ? Math.min(100, (m.crit / refMax) * 100)
            : null;
    return {
        label: _displayLabel(m.label),
        pct,
        color: utilColor(pct),
        warnPct,
        critPct,
        warnLabel: m.warn !== null ? fmtNum(m.warn, m.unit) : '',
        critLabel: m.crit !== null ? fmtNum(m.crit, m.unit) : '',
        valueLabel: fmtNum(m.value, m.unit),
    };
}

const perfRows = computed<PerfRow[]>(() => parsedMetrics.value.map(_toPerfRow));

// Pick the metric that best summarizes the service: prefer one with thresholds
// set (those drive the actual state), then fall back to the highest utilization.
// Anchors the Performance tab so the operator sees the headline value first.
const mainMetric = computed<PerfMetric | null>(() => {
    const metrics = parsedMetrics.value;
    if (!metrics.length) return null;
    const withThresholds = metrics.filter((m) => m.warn !== null || m.crit !== null);
    const candidates = withThresholds.length ? withThresholds : metrics;
    return [...candidates].sort((a, b) => utilPercent(b) - utilPercent(a))[0] ?? null;
});

const mainPerfRow = computed<PerfRow | null>(() =>
    mainMetric.value ? _toPerfRow(mainMetric.value) : null,
);

const otherPerfRows = computed<PerfRow[]>(() => {
    const main = mainMetric.value?.label;
    return perfRows.value.filter((r) => r.label !== main);
});

// Headline label/value above the bar — match what Checkmk's own Perf-O-Meter
// would show (e.g. "RAM usage" for Linux Memory). Falls back to the highest
// long-output percent line, then to the raw perf_data metric.
interface MainHeadline {
    label: string;
    valueLabel: string;
    pct: number;
    color: string;
}
const mainHeadline = computed<MainHeadline | null>(() => {
    const pf = perfometer.value;
    if (pf && pf.pcts.length > 0) {
        const pct = Math.min(100, pf.pcts[0]);
        // pf.label already encodes both name and value ("RAM 53.88%"), so we
        // don't repeat it as a separate detail line under the bar.
        return { label: pf.label, valueLabel: '', pct, color: utilColor(pct) };
    }
    const longRow = [...longOutputRows.value]
        .map((r) => {
            const pctMatch = r.value.match(/(\d+(?:\.\d+)?)\s*%/);
            return pctMatch && r.label ? { ...r, pct: parseFloat(pctMatch[1]) } : null;
        })
        .filter((r): r is NonNullable<typeof r> => r !== null)
        .sort((a, b) => b.pct - a.pct)[0];
    if (longRow) {
        const pct = Math.min(100, longRow.pct);
        return { label: longRow.label, valueLabel: longRow.value, pct, color: utilColor(pct) };
    }
    const row = mainPerfRow.value;
    if (!row) return null;
    return { label: row.label, valueLabel: row.valueLabel, pct: row.pct, color: row.color };
});

// Long output is a multi-line agent summary; each line tends to be
// "Label: <value>" — render as a structured two-column list instead of <pre>
// so it scans like a real summary table.
interface LongOutputRow {
    label: string;
    value: string;
}
const longOutputRows = computed<LongOutputRow[]>(() => {
    const raw = longOutputText.value;
    if (!raw) return [];
    return raw
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
            const idx = line.indexOf(':');
            if (idx <= 0) return { label: '', value: line };
            return { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() };
        });
});

// Mini-graph data — fetched lazily when the Performance tab is visible.
// 4 hours window matches Checkmk's default Perf-O-Meter graph; it's enough to
// see "trending toward warn" without being noisy.
const HISTORY_MINUTES = 240;
const historyData = ref<Record<string, MetricPoint[]>>({});
let _historyReqId = 0;

async function _loadHistory(): Promise<void> {
    historyData.value = {};
    const obj = props.object;
    const connId = props.connectionId;
    if (
        !connId ||
        !auth.accessToken ||
        !obj?.host_name ||
        (obj.type !== 'host' && obj.type !== 'service')
    )
        return;
    const reqId = ++_historyReqId;
    try {
        const res = await connectionsApi.metricHistory(
            connId,
            obj.host_name,
            obj.type === 'service' ? (obj.service_description ?? null) : null,
            HISTORY_MINUTES,
            auth.accessToken,
        );
        if (reqId === _historyReqId) historyData.value = res.series ?? {};
    } catch {
        if (reqId === _historyReqId) historyData.value = {};
    }
}

// Refetch on selection change, but only when the Performance tab actually has
// content to show — otherwise we'd hit metric-history for hosts that don't
// expose perf_data at all.
watch(
    [
        () => props.object?.type,
        () => props.object?.host_name,
        () => props.object?.service_description,
        () => props.connectionId,
        showPerformanceTab,
    ],
    ([, , , , show]) => {
        if (show) void _loadHistory();
        else historyData.value = {};
    },
);

const mainHistoryKey = computed(() => {
    const main = mainMetric.value?.label;
    if (!main) return null;
    // metric-history keys come straight from Checkmk's metric IDs (perf_data
    // labels), so a direct match works for normal services.
    return main in historyData.value ? main : null;
});

const mainThresholds = computed(() => {
    const m = mainMetric.value;
    if (!m) return null;
    return { warn: m.warn, crit: m.crit };
});

const isDark = ref(document.documentElement.classList.contains('dark'));
useMutationObserver(
    document.documentElement,
    () => {
        isDark.value = document.documentElement.classList.contains('dark');
    },
    { attributes: true, attributeFilter: ['class'] },
);
</script>

<style scoped>
.detail-drawer {
    /* Mounted as the slot of CmkSlideIn (vendor/cmk/components/CmkSlideIn);
       the SlideIn handles size, position, animation, focus-trap. We just
       provide the inner column layout. */
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
}

.detail-drawer__severity-bar {
    height: 3px;
    flex-shrink: 0;
}

.detail-drawer__header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.detail-drawer__title {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.detail-drawer__title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}

.detail-drawer__name {
    font-weight: var(--font-weight-semibold);
    color: var(--text);
    font-size: 14px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
}

.detail-drawer__type-pill {
    color: var(--text-muted);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 1px 6px;
    flex-shrink: 0;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__state-line {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.detail-drawer__since-text {
    font-size: 12px;
    font-weight: var(--font-weight-semibold);
    color: var(--text);
}

.detail-drawer--critical .detail-drawer__since-text,
.detail-drawer--unreachable .detail-drawer__since-text,
.detail-drawer--warn .detail-drawer__since-text {
    color: var(--text);
}

.detail-drawer__close,
.detail-drawer__icon-btn {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--bg-hover);
    color: var(--text-muted);
    border: none;
    cursor: pointer;
    font-size: 18px;
    line-height: 22px;
    text-align: center;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    flex-shrink: 0;
}

.detail-drawer__icon-btn {
    color: var(--text);
}

.detail-drawer__close:hover,
.detail-drawer__icon-btn:hover {
    color: var(--color-corporate-green-50, rgb(34 197 94));
    background: var(--bg);
}

.detail-drawer__body {
    flex: 1 1 auto;
    overflow-y: auto;
    padding: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.detail-drawer__tabs {
    flex: 1 1 auto;
    min-height: 0;
}

/* Override the vendor CmkTabs styling to fit the narrow Drawer: thin tab pills
   instead of the default boxy tab bar, no content-area border. */
/* stylelint-disable selector-pseudo-class-no-unknown */
.detail-drawer__tabs :deep(.cmk-tabs__list) {
    padding: 0 12px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
}

.detail-drawer__tabs :deep(.cmk-tab__li) {
    padding: 6px 10px !important;
    font-size: 11px;
    line-height: 1;
    border-radius: 0;
    border-color: transparent;
    background: transparent;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__tabs :deep(.cmk-tab__li[data-state='active']) {
    color: var(--text);
    background: transparent;
    border-bottom: 2px solid var(--color-corporate-green-50, rgb(34 197 94));
}

.detail-drawer__tabs :deep(.cmk-tab-content) {
    border: none;
    padding: 0;
}
/* stylelint-enable selector-pseudo-class-no-unknown */

.detail-drawer__pane {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 16px;
}

.detail-drawer__pane-section + .detail-drawer__pane-section {
    margin-top: 4px;
}

.detail-drawer__pane-heading {
    font-size: 10px;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.04em;
    font-weight: var(--font-weight-semibold);
    margin: 4px 0 6px;
}

.detail-drawer__tab-with-count {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.detail-drawer__tab-count {
    background: color-mix(in srgb, var(--color-state-warning) 20%, transparent);
    color: var(--text);
    font-size: 9px;
    line-height: 14px;
    min-width: 16px;
    padding: 0 4px;
    border-radius: 999px;
    text-align: center;
    font-weight: var(--font-weight-bold);
}

.detail-drawer__row {
    display: flex;
    align-items: baseline;
    gap: 10px;
}

.detail-drawer__state-pill {
    font-weight: var(--font-weight-bold);
    font-size: 11px;
    letter-spacing: 0.04em;
    padding: 2px 10px;
    border-radius: 999px;
    border: 1px solid currentcolor;
}

.detail-drawer__badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.detail-drawer__badge {
    font-size: 10px;
    font-weight: var(--font-weight-semibold);
    padding: 2px 8px;
    border-radius: 999px;
}

.detail-drawer__badge--ack {
    background: rgb(251 191 36 / 15%);
    color: var(--color-yellow-50);
    border: 1px solid rgb(251 191 36 / 40%);
}

.detail-drawer__badge--downtime {
    background: rgb(59 130 246 / 15%);
    color: var(--color-blue-50, var(--text));
    border: 1px solid rgb(59 130 246 / 40%);
}

.detail-drawer__badge--stale,
.detail-drawer__badge--muted {
    background: rgb(113 113 122 / 15%);
    color: var(--text-muted);
    border: 1px solid rgb(113 113 122 / 40%);
}

.detail-drawer__badge--flapping {
    background: rgb(168 85 247 / 15%);
    color: var(--color-purple-50, #c084fc);
    border: 1px solid rgb(168 85 247 / 40%);
}

.detail-drawer__output {
    font-family: var(--font-mono, monospace);
    font-size: 11px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    padding: 8px 10px;
    margin: 4px 0 0;
    overflow: auto;
    white-space: pre-wrap;
    max-height: 180px;
}

/* Long agent output is dimmer than the summary so the eye lands on the
   short status line first. */
.detail-drawer__output--long {
    color: var(--text-muted);
    max-height: 240px;
}

.detail-drawer__section h4 {
    font-size: 10px;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.04em;
    margin: 6px 0 4px;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__meta {
    display: grid;
    grid-template-columns: 90px 1fr;
    gap: 4px 12px;
    margin: 0;
    font-size: 11px;
}

.detail-drawer__meta dt {
    color: var(--text-muted);
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.04em;
    align-self: center;
}

.detail-drawer__meta dd {
    color: var(--text);
    margin: 0;
    overflow-wrap: anywhere;
}

/* Topology rows have variable-length labels ("Contact groups") and many chips
   that wouldn't fit in the 90px first column — stack vertically instead so
   each label gets its own line above the chips. */
.detail-drawer__meta--stacked {
    grid-template-columns: 1fr;
    gap: 6px;
}

.detail-drawer__meta--stacked dt {
    margin-top: 4px;
}

.detail-drawer__meta-value--warn {
    color: var(--color-yellow-50);
}

.detail-drawer__perf {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-drawer__perf-row {
    display: grid;
    grid-template-columns: 80px 1fr 90px;
    gap: 8px;
    align-items: center;
    font-size: 11px;
}

.detail-drawer__perf-label {
    color: var(--text-muted);
    text-transform: uppercase;
    font-size: 9px;
    letter-spacing: 0.04em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__perf-bar-wrap {
    position: relative;
    height: 8px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
}

.detail-drawer__perf-bar-wrap--lg {
    height: 14px;
    border-radius: 6px;
}

/* Headline metric block — visually anchored at the top of the Performance
   tab so the operator sees the status-driving value without scanning. */
.detail-drawer__main-metric {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 4px 0 6px;
}

.detail-drawer__main-metric-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
}

.detail-drawer__main-metric-label {
    color: var(--text-muted);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__main-metric-value {
    color: var(--text);
    font-size: 18px;
    font-weight: var(--font-weight-bold);
    font-variant-numeric: tabular-nums;
}

.detail-drawer__chart-wrap {
    height: 120px;
    margin: 4px 0;
}

/* Long output rendered as a label/value table — the human-readable summary
   that Checkmk already produces, so we treat it as the primary breakdown
   and skip duplicating the same data as bars below. */
.detail-drawer__output-rows {
    display: grid;
    grid-template-columns: minmax(80px, max-content) 1fr;
    gap: 3px 12px;
    margin: 0;
    font-size: 11px;
}

.detail-drawer__output-rows dt {
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__output-rows dd {
    color: var(--text);
    margin: 0;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
}

.detail-drawer__raw-metrics {
    border-top: 1px solid var(--border);
    padding-top: 6px;
}

.detail-drawer__raw-metrics > summary {
    cursor: pointer;
    color: var(--text-muted);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: var(--font-weight-semibold);
    padding: 4px 0;
    user-select: none;
}

/* stylelint-disable-next-line no-descending-specificity */
.detail-drawer__raw-metrics[open] > summary {
    color: var(--text);
}

.detail-drawer__raw-metrics > .detail-drawer__perf {
    margin-top: 6px;
}

.detail-drawer__perf-bar {
    height: 100%;
    transition: width 0.2s ease;
}

.detail-drawer__perf-mark {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
}

.detail-drawer__perf-mark--warn {
    background: rgb(255 208 0 / 80%);
}

.detail-drawer__perf-mark--crit {
    background: rgb(248 113 113 / 80%);
}

.detail-drawer__perf-value {
    color: var(--text);
    text-align: right;
    font-variant-numeric: tabular-nums;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__chips {
    /* Column count is set inline based on the chip count (zero-state chips are
       filtered out before render). */
    display: grid;
    gap: 6px;
}

.detail-drawer__chip {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1px;
    padding: 6px 4px;
    border-radius: var(--border-radius);
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    font: inherit;
    cursor: pointer;
    text-decoration: none;
    transition:
        transform 0.1s ease,
        border-color 0.1s ease;
}

.detail-drawer__chip:disabled {
    cursor: default;
}

.detail-drawer__chip:not(:disabled):hover {
    transform: translateY(-1px);
}

.detail-drawer__chip-count {
    font-size: 16px;
    font-weight: var(--font-weight-bold);
    line-height: 1;
}

.detail-drawer__chip-label {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    font-weight: var(--font-weight-semibold);
}

/* Chips track the global Checkmk state-color tokens (style.css) so they stay
   in sync with the rest of OrbVis/CMK. Background/border are tinted variants
   produced via color-mix; text uses the full state color. */
.detail-drawer__chip--crit {
    background: color-mix(in srgb, var(--color-state-critical) 12%, transparent);
    border-color: color-mix(in srgb, var(--color-state-critical) 35%, transparent);
}

.detail-drawer__chip--crit .detail-drawer__chip-count,
.detail-drawer__chip--crit .detail-drawer__chip-label {
    color: var(--color-state-critical);
}

.detail-drawer__chip--warn {
    background: color-mix(in srgb, var(--color-state-warning) 12%, transparent);
    border-color: color-mix(in srgb, var(--color-state-warning) 35%, transparent);
}

.detail-drawer__chip--warn .detail-drawer__chip-count,
.detail-drawer__chip--warn .detail-drawer__chip-label {
    color: var(--color-state-warning);
}

.detail-drawer__chip--unknown {
    background: color-mix(in srgb, var(--color-state-unknown) 12%, transparent);
    border-color: color-mix(in srgb, var(--color-state-unknown) 35%, transparent);
}

.detail-drawer__chip--unknown .detail-drawer__chip-count,
.detail-drawer__chip--unknown .detail-drawer__chip-label {
    color: var(--color-state-unknown);
}

.detail-drawer__chip--ok {
    background: color-mix(in srgb, var(--color-state-ok) 8%, transparent);
    border-color: color-mix(in srgb, var(--color-state-ok) 25%, transparent);
}

.detail-drawer__chip--ok .detail-drawer__chip-count,
.detail-drawer__chip--ok .detail-drawer__chip-label {
    color: var(--color-state-ok);
}

.detail-drawer__chip--zero {
    opacity: 0.45;
}

/* Inline chip rows for topology + labels sections — wraps the vendored
   CmkChip components with consistent spacing. */
.detail-drawer__chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 0;
}

.detail-drawer__label-key {
    color: var(--text-muted);
    margin-right: 4px;
}

/* Comments + downtimes lists share the row layout. */
.detail-drawer__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.detail-drawer__list-row {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    padding: 6px 8px;
    font-size: 11px;
}

.detail-drawer__list-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    color: var(--text-muted);
    font-size: 10px;
    margin-bottom: 2px;
    align-items: center;
}

.detail-drawer__list-author {
    color: var(--text);
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__list-tag {
    background: rgb(59 130 246 / 18%);
    color: var(--color-blue-50, var(--text));
    border: 1px solid rgb(59 130 246 / 40%);
    border-radius: 999px;
    padding: 0 6px;
    font-weight: var(--font-weight-semibold);
    letter-spacing: 0.04em;
}

.detail-drawer__list-text {
    color: var(--text);
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}

.detail-drawer__section--downtimes .detail-drawer__list-row {
    border: 1px solid rgb(59 130 246 / 35%);
    background: rgb(59 130 246 / 6%);
}

.detail-drawer__actions {
    border-top: 1px solid var(--border);
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
    background: var(--bg-surface);
}

.detail-drawer__actions--site {
    gap: 6px;
}

.detail-drawer__actions-title {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin: 0;
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__actions-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
}

/* CmkButton is inline-flex; stretch it across the grid cell so the actions
   line up. The --primary variant spans both columns for emphasis. */
.detail-drawer__action {
    width: 100%;
}

.detail-drawer__action--primary {
    grid-column: span 2;
}

/* Summary acts as the More-actions toggle and styled to match a sibling
   CmkButton (optional variant). */
.detail-drawer__btn {
    display: inline-flex;
    height: var(--dimension-10, 32px);
    padding: 0 8px;
    align-items: center;
    justify-content: center;
    background-color: var(--default-button-optional-color, var(--bg));
    border: 1px solid var(--button-optional-border-color, var(--border));
    color: var(--button-optional-text-color, var(--text));
    border-radius: var(--dimension-3, var(--border-radius));
    font-size: 12px;
    font-weight: bold;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
}

.detail-drawer__btn:hover {
    background: var(--bg-hover);
}

.detail-drawer__more {
    position: relative;
}

/* stylelint-disable-next-line no-descending-specificity */
.detail-drawer__more > summary {
    list-style: none;
    cursor: pointer;
}

.detail-drawer__more > summary::-webkit-details-marker {
    display: none;
}

.detail-drawer__btn--more {
    user-select: none;
}

.detail-drawer__more[open] > summary {
    background: var(--bg-hover);
    border-color: var(--text-muted);
}

.detail-drawer__more-menu {
    position: absolute;
    bottom: calc(100% + 4px);
    right: 0;
    min-width: 180px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    box-shadow: 0 -4px 12px rgb(0 0 0 / 35%);
    padding: 4px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    z-index: 2;
}

.detail-drawer__more-item {
    background: transparent;
    color: var(--text);
    border: none;
    border-radius: var(--border-radius);
    padding: 8px 10px;
    text-align: left;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
}

.detail-drawer__more-item:hover {
    background: var(--bg-hover);
}
</style>
