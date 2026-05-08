<template>
    <div
        v-if="object"
        class="detail-drawer"
        role="dialog"
        :aria-label="displayName"
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
                    <span class="detail-drawer__name" :title="displayName">{{ displayName }}</span>
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
                    <span v-if="sinceText" class="detail-drawer__since-text">{{ sinceText }}</span>
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
                <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                    <path
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.5"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M9.5 2.5h4v4M13.5 2.5L7 9M12 9v3.5a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1H7"
                    />
                </svg>
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

            <pre v-if="state.output" class="detail-drawer__output">{{ state.output }}</pre>

            <div v-if="perfRows.length" class="detail-drawer__section">
                <h4>{{ t('board.detailDrawer.perfdataLabel') }}</h4>
                <div class="detail-drawer__perf">
                    <div v-for="row in perfRows" :key="row.label" class="detail-drawer__perf-row">
                        <div class="detail-drawer__perf-label" :title="row.label">
                            {{ row.label }}
                        </div>
                        <div class="detail-drawer__perf-bar-wrap">
                            <div
                                class="detail-drawer__perf-bar"
                                :style="{ width: row.pct + '%', background: row.color }"
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
                        <div class="detail-drawer__perf-value">{{ row.valueLabel }}</div>
                    </div>
                </div>
            </div>

            <div
                v-if="serviceChips.length"
                class="detail-drawer__chips"
                :style="{ gridTemplateColumns: `repeat(${serviceChips.length}, 1fr)` }"
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
                    <span class="detail-drawer__chip-count">{{ chip.count }}</span>
                    <span class="detail-drawer__chip-label">{{ chip.label }}</span>
                </component>
            </div>

            <div
                v-if="hostChips.length"
                class="detail-drawer__chips"
                :style="{ gridTemplateColumns: `repeat(${hostChips.length}, 1fr)` }"
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
                    <span class="detail-drawer__chip-count">{{ chip.count }}</span>
                    <span class="detail-drawer__chip-label">{{ chip.label }}</span>
                </component>
            </div>

            <dl v-if="metaRows.length" class="detail-drawer__meta">
                <template v-for="row in metaRows" :key="row.label">
                    <dt>{{ row.label }}</dt>
                    <dd>{{ row.value }}</dd>
                </template>
            </dl>

            <div v-if="checkInfoRows.length" class="detail-drawer__section">
                <h4>{{ t('board.detailDrawer.checkInfo') }}</h4>
                <dl class="detail-drawer__meta">
                    <template v-for="row in checkInfoRows" :key="row.label">
                        <dt>{{ row.label }}</dt>
                        <dd :class="row.tone ? `detail-drawer__meta-value--${row.tone}` : ''">
                            {{ row.value }}
                        </dd>
                    </template>
                </dl>
            </div>
        </div>

        <footer v-if="!isSite" class="detail-drawer__actions">
            <h4 class="detail-drawer__actions-title">
                {{ t('board.detailDrawer.sectionActions') }}
            </h4>
            <div class="detail-drawer__actions-grid">
                <button
                    v-if="!state?.acknowledged && isProblematic"
                    type="button"
                    class="detail-drawer__btn detail-drawer__btn--primary"
                    @click="emit('acknowledge')"
                >
                    {{ t('board.detailDrawer.ackLabel') }}
                </button>
                <button
                    v-if="state?.acknowledged"
                    type="button"
                    class="detail-drawer__btn detail-drawer__btn--warn"
                    @click="emit('remove-ack')"
                >
                    {{ t('board.detailDrawer.removeAckLabel') }}
                </button>
                <button type="button" class="detail-drawer__btn" @click="emit('force-check')">
                    {{ t('board.detailDrawer.forceCheckLabel') }}
                </button>
                <button
                    v-if="!state?.in_downtime"
                    type="button"
                    class="detail-drawer__btn"
                    @click="emit('schedule-downtime')"
                >
                    {{ t('board.detailDrawer.scheduleDowntimeLabel') }}
                </button>
                <button
                    v-if="state?.in_downtime"
                    type="button"
                    class="detail-drawer__btn detail-drawer__btn--warn"
                    @click="emit('remove-downtime')"
                >
                    {{ t('board.detailDrawer.removeDowntimeLabel') }}
                </button>
                <button type="button" class="detail-drawer__btn" @click="emit('add-comment')">
                    {{ t('board.detailDrawer.addCommentLabel') }}
                </button>
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
            <a
                v-if="problemsUrlFull"
                :href="problemsUrlFull"
                target="_blank"
                rel="noopener noreferrer"
                class="detail-drawer__btn detail-drawer__btn--primary"
            >
                {{ t('board.detailDrawer.openProblems') }} ↗
            </a>
        </footer>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import type { BoardObject, ObjectState } from '@/types/api';
import { buildCheckmkUrl } from '@/utils/boardNavigation';
import { getBoardObjectName, getObjectTypeLabel } from '@/utils/naming';
import { parsePerfData, utilColor, utilPercent } from '@/utils/perf';
import { stateColor } from '@/utils/stateColors';
import { formatRelativeDuration, formatRelativeFuture } from '@/utils/time';

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
}>();

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
}>();

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
    kind: 'ack' | 'downtime' | 'stale' | 'muted';
}
const modifiers = computed<Modifier[]>(() => {
    const s = props.state;
    if (!s) return [];
    const list: Modifier[] = [];
    if (s.acknowledged) list.push({ label: 'ACK', kind: 'ack' });
    if (s.in_downtime) list.push({ label: 'DOWNTIME', kind: 'downtime' });
    if (s.stale) list.push({ label: 'STALE', kind: 'stale' });
    if (s.notifications_enabled === false) list.push({ label: 'MUTED', kind: 'muted' });
    return list;
});

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

    return rows;
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
    const abs = Math.abs(n);
    let str: string;
    if (abs >= 100) str = n.toFixed(0);
    else if (abs >= 10) str = n.toFixed(1);
    else str = n.toFixed(2);
    return `${str}${unit}`;
}

const perfRows = computed<PerfRow[]>(() => {
    const raw = props.state?.perf_data;
    if (!raw) return [];
    const metrics = parsePerfData(raw);
    if (!metrics.length) return [];
    return metrics.slice(0, 6).map((m) => {
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
            label: m.label,
            pct,
            color: utilColor(pct),
            warnPct,
            critPct,
            warnLabel: m.warn !== null ? fmtNum(m.warn, m.unit) : '',
            critLabel: m.crit !== null ? fmtNum(m.crit, m.unit) : '',
            valueLabel: fmtNum(m.value, m.unit),
        };
    });
});
</script>

<style scoped>
.detail-drawer {
    /* Absolute (not fixed) so the drawer stays inside the board container and
       respects the OrbVis/Checkmk app header sitting above it. */
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 360px;
    max-width: 100vw;
    background: var(--bg-surface);
    border-left: 1px solid var(--border);
    z-index: 30;
    display: flex;
    flex-direction: column;
    box-shadow: -4px 0 16px rgb(0 0 0 / 40%);
    animation: slide-in 0.18s ease-out;
    min-height: 0;

    /* Local tokens for chip + warn-button tints. Kept here (not in style.css)
       because they are drawer-internal accents on top of the global state-color
       system. */
    --chip-crit-fg: rgb(248 113 113);
    --chip-crit-border: rgb(248 113 113 / 35%);
    --chip-warn-fg: rgb(255 208 0);
    --chip-warn-border: rgb(255 208 0 / 35%);
    --chip-warn-border-hover: rgb(255 208 0 / 55%);
    --chip-unknown-fg: rgb(251 146 60);
    --chip-unknown-border: rgb(251 146 60 / 35%);
    --chip-ok-fg: rgb(74 222 128);
    --chip-ok-border: rgb(74 222 128 / 25%);
    --primary-btn-fg: rgb(0 0 0 / 90%);
}

@keyframes slide-in {
    from {
        transform: translateX(100%);
    }

    to {
        transform: translateX(0);
    }
}

/* Vue <Transition name="drawer-slide"> applies these classes on close so the
 * drawer slides out instead of vanishing. The mount-time slide-in is still
 * driven by the keyframe above. */
.drawer-slide-leave-active.detail-drawer {
    transition: transform 0.18s ease-in;
    animation: none;
}

.drawer-slide-leave-to.detail-drawer {
    transform: translateX(100%);
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
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
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

.detail-drawer__chip--crit {
    background: rgb(248 113 113 / 12%);
    border-color: var(--chip-crit-border);
}

.detail-drawer__chip--crit .detail-drawer__chip-count,
.detail-drawer__chip--crit .detail-drawer__chip-label {
    color: var(--chip-crit-fg);
}

.detail-drawer__chip--warn {
    background: rgb(255 208 0 / 12%);
    border-color: var(--chip-warn-border);
}

.detail-drawer__chip--warn .detail-drawer__chip-count,
.detail-drawer__chip--warn .detail-drawer__chip-label {
    color: var(--chip-warn-fg);
}

.detail-drawer__chip--unknown {
    background: rgb(251 146 60 / 12%);
    border-color: var(--chip-unknown-border);
}

.detail-drawer__chip--unknown .detail-drawer__chip-count,
.detail-drawer__chip--unknown .detail-drawer__chip-label {
    color: var(--chip-unknown-fg);
}

.detail-drawer__chip--ok {
    background: rgb(74 222 128 / 8%);
    border-color: var(--chip-ok-border);
}

.detail-drawer__chip--ok .detail-drawer__chip-count,
.detail-drawer__chip--ok .detail-drawer__chip-label {
    color: var(--chip-ok-fg);
}

.detail-drawer__chip--zero {
    opacity: 0.45;
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

.detail-drawer__btn {
    padding: 8px 10px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    font-size: 12px;
    font-weight: var(--font-weight-semibold);
    cursor: pointer;
    text-align: center;
    text-decoration: none;
    transition:
        background 0.1s,
        border-color 0.1s;
}

.detail-drawer__btn:hover {
    background: var(--bg-hover);
    border-color: var(--text-muted);
}

.detail-drawer__btn--primary {
    grid-column: span 2;
    background: var(--color-corporate-green-50, rgb(34 197 94));
    color: var(--primary-btn-fg);
    border-color: var(--color-corporate-green-50, rgb(34 197 94));
}

.detail-drawer__btn--primary:hover {
    background: var(--color-corporate-green-40, rgb(22 163 74));
    border-color: var(--color-corporate-green-40, rgb(22 163 74));
}

.detail-drawer__btn--warn {
    background: rgb(255 208 0 / 12%);
    color: var(--chip-warn-fg);
    border-color: var(--chip-warn-border);
}

.detail-drawer__btn--warn:hover {
    background: rgb(255 208 0 / 18%);
    border-color: var(--chip-warn-border-hover);
}

.detail-drawer__more {
    position: relative;
}

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
