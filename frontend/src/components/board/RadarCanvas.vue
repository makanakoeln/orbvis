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
                    class="w-7 h-7 text-zinc-600"
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
            <p class="text-zinc-500 text-sm font-medium">No objects found</p>
            <p class="text-zinc-600 text-xs mt-1">Check the Radar filter settings</p>
        </div>

        <!-- Summary bar -->
        <div v-else class="mb-5 flex items-center gap-4 flex-wrap">
            <span class="text-xs text-zinc-500">{{ sortedStates.length }} objects</span>
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
                            class="text-zinc-400 opacity-70"
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
                            class="text-zinc-400 opacity-70"
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
            return 'bg-red-500/8 ring-red-500/20 hover:shadow-red-900/20';
        case 'UNREACHABLE':
            return 'bg-orange-500/8 ring-orange-500/20 hover:shadow-orange-900/20';
        case 'WARNING':
        case 'UNKNOWN':
            return 'bg-[#ffd000]/8 ring-[#ffd000]/20 hover:shadow-yellow-900/20';
        case 'UP':
        case 'OK':
            return 'bg-green-500/8 ring-green-500/20 hover:shadow-green-900/20';
        default:
            return 'bg-[var(--default-form-element-bg-color)] ring-[var(--border)]';
    }
}

function nameClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'text-red-300';
        case 'UNREACHABLE':
            return 'text-orange-300';
        case 'WARNING':
        case 'UNKNOWN':
            return 'text-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'text-green-300';
        default:
            return 'text-zinc-400';
    }
}

function badgeClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'bg-red-500/15 text-red-400';
        case 'UNREACHABLE':
            return 'bg-orange-500/15 text-orange-400';
        case 'WARNING':
        case 'UNKNOWN':
            return 'bg-[#ffd000]/15 text-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'bg-green-500/15 text-green-400';
        default:
            return 'bg-zinc-700/50 text-zinc-500';
    }
}

function stateDotClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'bg-red-400';
        case 'UNREACHABLE':
            return 'bg-orange-400';
        case 'WARNING':
        case 'UNKNOWN':
            return 'bg-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'bg-green-400';
        default:
            return 'bg-zinc-500';
    }
}

function stateTextClass(state: string): string {
    switch (state) {
        case 'DOWN':
        case 'CRITICAL':
            return 'text-red-400';
        case 'UNREACHABLE':
            return 'text-orange-400';
        case 'WARNING':
        case 'UNKNOWN':
            return 'text-[#ffd000]';
        case 'UP':
        case 'OK':
            return 'text-green-400';
        default:
            return 'text-zinc-500';
    }
}
</script>
