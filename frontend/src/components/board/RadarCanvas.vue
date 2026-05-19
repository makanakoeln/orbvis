<template>
    <div class="flex-1 overflow-auto bg-[var(--bg)] p-6">
        <!-- Empty state -->
        <div
            v-if="!sortedStates.length"
            class="flex flex-col items-center justify-center h-full text-center"
        >
            <div
                class="w-14 h-14 rounded-2xl bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--border)] flex items-center justify-center mb-4"
            >
                <svg
                    class="w-7 h-7 text-[var(--text-muted)]"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="1.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M9.348 14.652a3.75 3.75 0 010-5.304m5.304 0a3.75 3.75 0 010 5.304m-7.425 2.121a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.807-3.808-9.98 0-13.788m13.788 0c3.808 3.807 3.808 9.98 0 13.788M12 12h.008v.008H12V12z"
                    />
                </svg>
            </div>
            <p class="text-[var(--text-muted)] text-sm font-medium">
                {{ t('boardSettings.radarEmptyTitle') }}
            </p>
            <p class="text-[var(--text-muted)] text-xs mt-1 inline-flex items-center gap-1.5">
                <span>{{ t('boardSettings.radarEmptyHintLead') }}</span>
                <svg
                    class="w-3.5 h-3.5 inline-block"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="1.5"
                    aria-hidden="true"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
                    />
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                </svg>
            </p>
        </div>

        <!-- Summary bar -->
        <div v-else class="mb-5 flex items-center gap-4 flex-wrap">
            <span class="text-xs text-[var(--text-muted)]">{{ sortedStates.length }} objects</span>
            <div class="flex items-center gap-3 flex-wrap">
                <span
                    v-for="s in summary"
                    :key="s.state"
                    class="flex items-center gap-1.5 text-xs font-medium"
                    :class="stateTextClass(s.state)"
                >
                    <span class="w-1.5 h-1.5 rounded-full" :class="stateDotClass(s.state)" />
                    {{ s.count }} {{ s.state }}
                </span>
            </div>
        </div>

        <!-- Grid -->
        <div
            class="grid gap-2.5"
            style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))"
        >
            <div
                v-for="state in sortedStates"
                :key="state.object_id"
                class="rounded-xl p-3.5 ring-1 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg cursor-pointer"
                :class="cardClass(state.state)"
                @click="onCardClick(state, $event)"
            >
                <!-- Name -->
                <div class="flex items-start justify-between gap-2 mb-2">
                    <span
                        class="font-mono text-xs font-semibold leading-tight break-all"
                        :class="nameClass(state.state)"
                    >
                        {{ displayName(state) }}
                    </span>
                    <!-- Ack / Downtime icons -->
                    <div class="flex gap-1 shrink-0 mt-0.5">
                        <span
                            v-if="state.acknowledged"
                            title="Acknowledged"
                            class="text-[var(--text-muted)] opacity-70"
                        >
                            <svg
                                class="w-3 h-3"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                            </svg>
                        </span>
                        <span
                            v-if="state.in_downtime"
                            title="In downtime"
                            class="text-[var(--text-muted)] opacity-70"
                        >
                            <svg
                                class="w-3 h-3"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                            </svg>
                        </span>
                    </div>
                </div>

                <!-- State badge -->
                <span
                    class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md"
                    :class="badgeClass(state.state)"
                >
                    <span class="w-1 h-1 rounded-full" :class="stateDotClass(state.state)" />
                    {{ state.state }}
                </span>

                <!-- Output -->
                <p
                    v-if="state.output"
                    class="text-[11px] mt-2 leading-snug opacity-60 line-clamp-2"
                    :class="nameClass(state.state)"
                >
                    {{ state.output }}
                </p>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

import type { BoardObject, ObjectState } from '@/types/api';

const props = defineProps<{
    states: Record<string, ObjectState>;
    checkmkUrl?: string | null;
    readonly?: boolean;
    filterNeedle?: string;
}>();

const emit = defineEmits<{
    'object-click': [obj: BoardObject, event: MouseEvent];
}>();

function stateToBoardObject(state: ObjectState): BoardObject {
    if (state.type === 'service' && state.object_id.includes(';')) {
        const [host, svc] = state.object_id.split(';', 2);
        return {
            id: state.object_id,
            type: 'service',
            host_name: host,
            service_description: svc,
            x: 0,
            y: 0,
            z: 0,
            url_target: '_blank',
        };
    }
    return {
        id: state.object_id,
        type: 'host',
        host_name: state.object_id,
        x: 0,
        y: 0,
        z: 0,
        url_target: '_blank',
    };
}

function onCardClick(state: ObjectState, event: MouseEvent) {
    emit('object-click', stateToBoardObject(state), event);
}

// State severity for sorting (worst first)
const severity: Record<string, number> = {
    DOWN: 5,
    CRITICAL: 5,
    UNREACHABLE: 4,
    WARNING: 3,
    UNKNOWN: 3,
    PENDING: 1,
    UP: 0,
    OK: 0,
};

const sortedStates = computed(() => {
    const needle = (props.filterNeedle ?? '').trim().toLowerCase();
    const all = Object.values(props.states).sort(
        (a, b) => (severity[b.state] ?? 0) - (severity[a.state] ?? 0),
    );
    if (!needle) return all;
    // Radar cards have no spatial layout, so filtering (rather than dimming)
    // produces a more useful view: only matching hosts/services remain visible.
    return all.filter((s) => displayName(s).toLowerCase().includes(needle));
});

const summary = computed(() => {
    const counts: Record<string, number> = {};
    for (const s of sortedStates.value) {
        counts[s.state] = (counts[s.state] ?? 0) + 1;
    }
    return Object.entries(counts)
        .map(([state, count]) => ({ state, count }))
        .sort((a, b) => (severity[b.state] ?? 0) - (severity[a.state] ?? 0));
});

function displayName(state: ObjectState): string {
    if (state.type === 'service' && state.object_id.includes(';')) {
        const [host, svc] = state.object_id.split(';', 2);
        return `${host} · ${svc}`;
    }
    return state.object_id;
}

function cardClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'bg-[var(--color-light-red-50)]/8 ring-[var(--color-light-red-50)]/20 hover:shadow-red-900/20';
        case 'UNREACHABLE':
            return 'bg-orange-500/8 ring-orange-500/20 hover:shadow-orange-900/20';
        case 'WARNING':
        case 'UNKNOWN':
            return 'bg-[#ffd000]/8 ring-[#ffd000]/20 hover:shadow-yellow-900/20';
        case 'UP':
        case 'OK':
            return 'bg-[var(--color-corporate-green-50)]/8 ring-[var(--color-corporate-green-50)]/20 hover:shadow-green-900/20';
        default:
            return 'bg-[var(--default-form-element-bg-color)] ring-[var(--border)]';
    }
}

function nameClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'text-[var(--color-light-red-40)]';
        case 'UNREACHABLE':
            return 'text-orange-300';
        case 'WARNING':
        case 'UNKNOWN':
            return 'text-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'text-[var(--color-corporate-green-50)]';
        default:
            return 'text-[var(--text-muted)]';
    }
}

function badgeClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'bg-[var(--color-light-red-50)]/15 text-[var(--color-light-red-40)]';
        case 'UNREACHABLE':
            return 'bg-orange-500/15 text-orange-400';
        case 'WARNING':
        case 'UNKNOWN':
            return 'bg-[#ffd000]/15 text-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'bg-[var(--color-corporate-green-50)]/15 text-[var(--color-corporate-green-50)]';
        default:
            return 'bg-[var(--bg-hover)] text-[var(--text-muted)]';
    }
}

function stateDotClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'bg-[var(--color-light-red-40)]';
        case 'UNREACHABLE':
            return 'bg-orange-400';
        case 'WARNING':
        case 'UNKNOWN':
            return 'bg-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'bg-[var(--color-corporate-green-50)]';
        default:
            return 'bg-[var(--color-pending)]';
    }
}

function stateTextClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'text-[var(--color-light-red-40)]';
        case 'UNREACHABLE':
            return 'text-orange-400';
        case 'WARNING':
        case 'UNKNOWN':
            return 'text-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'text-[var(--color-corporate-green-50)]';
        default:
            return 'text-[var(--text-muted)]';
    }
}
</script>
