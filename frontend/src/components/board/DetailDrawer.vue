<template>
    <div v-if="object" class="detail-drawer" role="dialog" :aria-label="displayName" @click.stop>
        <header class="detail-drawer__header">
            <span
                v-if="state"
                class="detail-drawer__state-dot"
                :style="{ background: stateColor(state.state) }"
            />
            <div class="detail-drawer__title">
                <div class="detail-drawer__name">{{ displayName }}</div>
                <div class="detail-drawer__type">{{ typeLabel }}</div>
            </div>
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
            <div class="detail-drawer__row">
                <span
                    class="detail-drawer__state-pill"
                    :style="{
                        color: stateColor(state.state),
                        borderColor: stateColor(state.state),
                    }"
                >
                    {{ state.state }}
                </span>
                <span v-if="sinceLabel" class="detail-drawer__since">{{ sinceLabel }}</span>
            </div>

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

            <div v-if="state.services_summary" class="detail-drawer__section">
                <h4>{{ t('board.detailDrawer.servicesSummary') }}</h4>
                <ul class="detail-drawer__services">
                    <li v-if="state.services_summary.critical">
                        <span class="dot" :style="{ background: stateColor('CRITICAL') }" />
                        {{ state.services_summary.critical }} critical
                    </li>
                    <li v-if="state.services_summary.warning">
                        <span class="dot" :style="{ background: stateColor('WARNING') }" />
                        {{ state.services_summary.warning }} warning
                    </li>
                    <li v-if="state.services_summary.unknown">
                        <span class="dot" :style="{ background: stateColor('UNKNOWN') }" />
                        {{ state.services_summary.unknown }} unknown
                    </li>
                    <li>
                        <span class="dot" :style="{ background: stateColor('OK') }" />
                        {{ state.services_summary.ok }} OK
                    </li>
                </ul>
            </div>
        </div>

        <footer class="detail-drawer__actions">
            <a
                v-if="checkmkUrlFull"
                :href="checkmkUrlFull"
                target="_blank"
                rel="noopener noreferrer"
                class="detail-drawer__btn detail-drawer__btn--primary"
            >
                {{ t('board.detailDrawer.openInCheckmk') }}
            </a>
            <template v-if="!isSite">
                <button
                    v-if="!state?.acknowledged && isProblematic"
                    type="button"
                    class="detail-drawer__btn"
                    @click="emit('acknowledge')"
                >
                    {{ t('contextMenu.acknowledge') }}
                </button>
                <button
                    v-if="state?.acknowledged"
                    type="button"
                    class="detail-drawer__btn"
                    @click="emit('remove-ack')"
                >
                    {{ t('contextMenu.removeAck') }}
                </button>
                <button type="button" class="detail-drawer__btn" @click="emit('schedule-downtime')">
                    {{ t('contextMenu.scheduleDowntime') }}
                </button>
                <button
                    v-if="state?.in_downtime"
                    type="button"
                    class="detail-drawer__btn"
                    @click="emit('remove-downtime')"
                >
                    {{ t('contextMenu.removeDowntime') }}
                </button>
                <button type="button" class="detail-drawer__btn" @click="emit('force-check')">
                    {{ t('contextMenu.forceCheck') }}
                </button>
                <button type="button" class="detail-drawer__btn" @click="emit('add-comment')">
                    {{ t('contextMenu.addComment') }}
                </button>
                <button
                    v-if="state?.notifications_enabled !== false"
                    type="button"
                    class="detail-drawer__btn"
                    @click="emit('disable-notifications')"
                >
                    {{ t('contextMenu.disableNotifications') }}
                </button>
                <button
                    v-else
                    type="button"
                    class="detail-drawer__btn"
                    @click="emit('enable-notifications')"
                >
                    {{ t('contextMenu.enableNotifications') }}
                </button>
            </template>
        </footer>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import type { BoardObject, ObjectState } from '@/types/api';
import { buildCheckmkUrl } from '@/utils/boardNavigation';
import { getBoardObjectName, getObjectTypeLabel } from '@/utils/naming';
import { stateColor } from '@/utils/stateColors';

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

const PROBLEM_STATES = new Set(['CRITICAL', 'WARNING', 'UNKNOWN', 'DOWN', 'UNREACHABLE']);
const isProblematic = computed(() => (props.state ? PROBLEM_STATES.has(props.state.state) : false));
const isSite = computed(() => props.object?.type === 'site');

const { t } = useI18n();

const displayName = computed(() => (props.object ? getBoardObjectName(props.object) : ''));
const typeLabel = computed(() => (props.object ? getObjectTypeLabel(props.object) : ''));

const checkmkUrlFull = computed(() =>
    props.object ? buildCheckmkUrl(props.object, props.checkmkUrl ?? null) : null,
);

function formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    const m = Math.floor(seconds / 60);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ${m % 60}m`;
    const d = Math.floor(h / 24);
    return `${d}d ${h % 24}h`;
}

const sinceLabel = computed(() => {
    const ts = props.state?.last_state_change;
    if (!ts) return null;
    const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
    return t('board.hover.since', { duration: formatDuration(seconds) });
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
    if (s.site_id) rows.push({ label: t('board.detailDrawer.site'), value: s.site_id });
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
                duration: formatDuration(Math.max(0, now - s.last_check)),
            }),
        });
    } else if (s.last_check === 0) {
        rows.push({
            label: t('board.detailDrawer.lastCheck'),
            value: t('board.detailDrawer.never'),
        });
    }

    if (s.next_check && s.next_check > 0) {
        const delta = s.next_check - now;
        if (delta < 0) {
            rows.push({
                label: t('board.detailDrawer.nextCheck'),
                value: `${t('board.detailDrawer.overdue')} (${formatDuration(Math.abs(delta))})`,
                tone: 'warn',
            });
        } else {
            rows.push({
                label: t('board.detailDrawer.nextCheck'),
                value: t('board.detailDrawer.timeIn', { duration: formatDuration(delta) }),
            });
        }
    }

    return rows;
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

.detail-drawer__header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.detail-drawer__state-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
}

.detail-drawer__title {
    flex: 1;
    min-width: 0;
}

.detail-drawer__name {
    font-weight: var(--font-weight-semibold);
    color: var(--text);
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-drawer__type {
    color: var(--text-muted);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 2px;
}

.detail-drawer__close {
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
}

.detail-drawer__close:hover {
    color: var(--text);
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
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid currentcolor;
    background: rgb(255 255 255 / 4%);
}

.detail-drawer__since {
    color: var(--text-muted);
    font-size: 11px;
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

.detail-drawer__services {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-drawer__services li {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text);
    font-size: 12px;
}

.detail-drawer__services .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

.detail-drawer__actions {
    border-top: 1px solid var(--border);
    padding: 10px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    flex-shrink: 0;
    background: var(--bg-surface);
}

.detail-drawer__btn {
    flex: 1 1 calc(50% - 3px);
    min-width: 0;
    padding: 6px 10px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    font-size: 11px;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
}

.detail-drawer__btn:hover {
    background: var(--bg-hover);
}

.detail-drawer__btn--primary {
    flex-basis: 100%;
    background: var(--bg-hover);
    color: var(--text);
    border-color: var(--text-muted);
    font-weight: var(--font-weight-semibold);
}

.detail-drawer__btn--primary:hover {
    background: var(--bg);
    border-color: var(--text);
}
</style>
