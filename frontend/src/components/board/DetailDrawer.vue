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

            <p v-if="state.alias" class="detail-drawer__sub">{{ state.alias }}</p>
            <p v-if="state.address" class="detail-drawer__sub">{{ state.address }}</p>
            <p v-if="state.site_id" class="detail-drawer__sub">@{{ state.site_id }}</p>

            <pre v-if="state.output" class="detail-drawer__output">{{ state.output }}</pre>

            <div v-if="state.services_summary" class="detail-drawer__services">
                <h4>{{ t('board.detailDrawer.servicesSummary') }}</h4>
                <ul>
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
            <button type="button" class="detail-drawer__btn" @click="emit('acknowledge')">
                {{ t('contextMenu.acknowledge') }}
            </button>
            <button type="button" class="detail-drawer__btn" @click="emit('schedule-downtime')">
                {{ t('contextMenu.scheduleDowntime') }}
            </button>
            <button type="button" class="detail-drawer__btn" @click="emit('force-check')">
                {{ t('contextMenu.forceCheck') }}
            </button>
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
    'schedule-downtime': [];
    'force-check': [];
}>();

const { t } = useI18n();

const displayName = computed(() => (props.object ? getBoardObjectName(props.object) : ''));
const typeLabel = computed(() => (props.object ? getObjectTypeLabel(props.object) : ''));

const checkmkUrlFull = computed(() =>
    props.object ? buildCheckmkUrl(props.object, props.checkmkUrl ?? null) : null,
);

const sinceLabel = computed(() => {
    const ts = props.state?.last_state_change;
    if (!ts) return null;
    const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
    if (seconds < 60) return t('board.hover.since', { duration: `${seconds}s` });
    const m = Math.floor(seconds / 60);
    if (m < 60) return t('board.hover.since', { duration: `${m}m` });
    const h = Math.floor(m / 60);
    if (h < 24) return t('board.hover.since', { duration: `${h}h ${m % 60}m` });
    const d = Math.floor(h / 24);
    return t('board.hover.since', { duration: `${d}d ${h % 24}h` });
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
</script>

<style scoped>
.detail-drawer {
    position: fixed;
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
}

@keyframes slide-in {
    from {
        transform: translateX(100%);
    }

    to {
        transform: translateX(0);
    }
}

.detail-drawer__header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
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
    flex: 1;
    overflow-y: auto;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
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

.detail-drawer__sub {
    color: var(--text-muted);
    font-size: 11px;
    margin: 0;
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
    overflow-x: auto;
    white-space: pre-wrap;
}

.detail-drawer__services h4 {
    font-size: 11px;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.04em;
    margin: 8px 0 6px;
}

.detail-drawer__services ul {
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
    padding: 12px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
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
    background: var(--accent, #4ade80);
    color: var(--bg);
    border-color: var(--accent, #4ade80);
    font-weight: var(--font-weight-semibold);
}
</style>
