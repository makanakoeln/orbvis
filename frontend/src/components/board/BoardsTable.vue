<template>
    <div
        class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
        style="max-width: 1100px; margin: 0 auto"
    >
        <table class="w-full text-sm" style="border-collapse: separate; border-spacing: 0">
            <thead>
                <tr class="border-b border-[var(--border)]">
                    <th
                        v-if="auth.canCreateBoards"
                        class="text-left"
                        style="padding: 6px 8px 6px 12px; width: 28px"
                    >
                        <CmkCheckbox
                            v-if="capabilities.formSpecs"
                            :model-value="allSelected"
                            @update:model-value="$emit('toggle-select-all', $event)"
                        />
                        <input
                            v-else
                            type="checkbox"
                            :checked="allSelected"
                            @change="
                                $emit(
                                    'toggle-select-all',
                                    ($event.target as HTMLInputElement).checked,
                                )
                            "
                        />
                    </th>
                    <th
                        v-for="col in visibleColumns"
                        :key="col.id"
                        class="text-sm font-semibold text-[var(--text-muted)] tracking-wider select-none"
                        :class="[
                            col.align === 'right' ? 'text-right' : 'text-left',
                            col.sortable ? 'cursor-pointer hover:text-[var(--text)]' : '',
                        ]"
                        style="padding: 6px 12px"
                        :aria-sort="ariaSortFor(col.id)"
                        @click="col.sortable && setSort(col.id)"
                    >
                        <span class="inline-flex items-center" style="gap: 4px">
                            {{ t(col.label) }}
                            <span
                                v-if="col.sortable"
                                class="text-[10px]"
                                :class="
                                    sortState.col === col.id
                                        ? 'text-[var(--color-corporate-green-50)]'
                                        : 'text-[var(--text-muted)]/40'
                                "
                                aria-hidden="true"
                            >
                                {{
                                    sortState.col === col.id
                                        ? sortState.dir === 'asc'
                                            ? '▲'
                                            : '▼'
                                        : '↕'
                                }}
                            </span>
                        </span>
                    </th>
                </tr>
            </thead>
            <tbody class="divide-y divide-[var(--border)]">
                <tr
                    v-for="map in sortedBoards"
                    :key="map.name"
                    class="hover:bg-[var(--bg-hover)] transition-colors"
                    :class="
                        selectedBoards.has(map.name) ? 'bg-[var(--color-corporate-green-50)]/8' : ''
                    "
                >
                    <td
                        v-if="auth.canCreateBoards"
                        class="align-middle"
                        style="padding: 6px 8px 6px 12px"
                        @click.stop
                    >
                        <CmkCheckbox
                            v-if="capabilities.formSpecs"
                            :model-value="selectedBoards.has(map.name)"
                            @update:model-value="$emit('toggle-select', map.name)"
                        />
                        <input
                            v-else
                            type="checkbox"
                            :checked="selectedBoards.has(map.name)"
                            @change="$emit('toggle-select', map.name)"
                        />
                    </td>
                    <td class="align-middle" style="padding: 6px 12px">
                        <div class="flex flex-wrap items-center" style="gap: 6px">
                            <router-link
                                :to="`/boards/${map.name}`"
                                class="font-semibold text-[var(--text)] hover:text-[var(--color-corporate-green-50)] transition-colors"
                                :title="map.alias || map.name"
                            >
                                {{ map.alias || map.name }}
                            </router-link>
                            <!-- Board-management flags inline with the name (admin-only);
                                 a dedicated mostly-empty column isn't worth it. -->
                            <template v-if="auth.isAdmin">
                                <span
                                    v-if="map.show_in_lists === false"
                                    class="text-[10px] rounded-md font-medium bg-[var(--bg-surface)] text-[var(--text-muted)] ring-1 ring-[var(--default-border-color)]/60"
                                    style="padding: var(--dimension-2) 5px"
                                    :title="t('home.hiddenBoard')"
                                >
                                    {{ t('home.hidden') }}
                                </span>
                                <span
                                    v-if="map.readonly"
                                    class="text-[10px] rounded-md font-medium bg-[var(--bg-surface)] text-[var(--text-muted)] ring-1 ring-[var(--default-border-color)]/60"
                                    style="padding: var(--dimension-2) 5px"
                                    :title="t('home.readonlyBoardTitle')"
                                >
                                    {{ t('home.readonly') }}
                                </span>
                                <span
                                    v-if="map.rotation_interval > 0"
                                    class="rounded-full font-medium bg-[var(--color-warning)]/20 text-[var(--color-yellow-50)] ring-1 ring-[var(--color-warning)]/30"
                                    style="font-size: 11px; padding: var(--dimension-2) 6px"
                                    :title="
                                        t('home.rotationBadgeTitle', { n: map.rotation_interval })
                                    "
                                >
                                    ↻ {{ map.rotation_interval }}s
                                </span>
                            </template>
                        </div>
                    </td>
                    <td class="align-middle" style="padding: 6px 12px">
                        <span
                            class="rounded-md font-medium"
                            style="font-size: 11px; padding: var(--dimension-2) 6px"
                            :class="typeBadgeClass(map.view.type)"
                        >
                            {{ boardTypeLabel(map.view.type) }}
                        </span>
                    </td>
                    <td v-if="auth.isAdmin" class="align-middle" style="padding: 6px 12px">
                        <div class="flex items-center min-w-0" style="gap: 6px">
                            <svg
                                class="shrink-0 text-[var(--text-muted)]"
                                style="width: 12px; height: 12px"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3"
                                />
                            </svg>
                            <span
                                class="text-[var(--text-muted)] font-mono truncate"
                                :title="map.connection_id"
                            >
                                {{ map.connection_id }}
                            </span>
                        </div>
                    </td>
                    <td
                        class="align-middle text-right text-[var(--text-muted)] tabular-nums"
                        style="padding: 6px 12px"
                    >
                        <span v-if="isDynamic(map)" class="italic">
                            {{ t('home.dynamicObjects') }}
                        </span>
                        <span v-else>{{ map.object_count }}</span>
                    </td>
                    <td
                        v-if="auth.isAdmin || anyEditable"
                        class="align-middle text-right"
                        style="padding: 6px 12px"
                        @click.stop
                    >
                        <div class="inline-flex items-center" style="gap: var(--dimension-2)">
                            <button
                                v-if="(auth.isAdmin || map.can_edit) && !map.readonly"
                                class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-50)]/10 transition-all"
                                :title="t('board.settingsTitle')"
                                @click="$emit('open-settings', map)"
                            >
                                <svg
                                    style="width: 14px; height: 14px"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
                                    />
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                                    />
                                </svg>
                            </button>
                            <button
                                v-if="auth.canCreateBoards"
                                class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--color-yellow-50)] hover:bg-[var(--color-warning)]/10 transition-all"
                                :title="t('admin.cloneBoard')"
                                @click="$emit('clone', map)"
                            >
                                <svg
                                    style="width: 14px; height: 14px"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"
                                    />
                                </svg>
                            </button>
                            <button
                                v-if="auth.canCreateBoards"
                                class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-white/5 transition-all"
                                :title="t('admin.exportBoard')"
                                @click="$emit('export', map.name)"
                            >
                                <svg
                                    style="width: 14px; height: 14px"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                                    />
                                </svg>
                            </button>
                            <button
                                v-if="auth.canCreateBoards"
                                class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--color-light-red-40)] hover:bg-[var(--color-light-red-50)]/10 transition-all"
                                :title="t('admin.deleteBoard', { name: map.alias || map.name })"
                                @click="$emit('delete', map)"
                            >
                                <svg
                                    style="width: 14px; height: 14px"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                                    />
                                </svg>
                            </button>
                        </div>
                    </td>
                </tr>
                <tr v-if="boards.length === 0">
                    <td
                        :colspan="visibleColumns.length + (auth.canCreateBoards ? 1 : 0)"
                        class="text-center text-[var(--text-muted)] text-sm"
                        style="padding: 40px 0"
                    >
                        {{ t('home.noSearchResults', { q: searchQuery }) }}
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';
import { useAuthStore } from '@/stores/auth';
import { useCapabilitiesStore } from '@/stores/capabilities';
import type { BoardRead } from '@/types/api';

const props = defineProps<{
    boards: BoardRead[];
    selectedBoards: Set<string>;
    searchQuery: string;
    allSelected: boolean;
}>();

defineEmits<{
    (e: 'toggle-select', name: string): void;
    (e: 'toggle-select-all', checked: boolean): void;
    (e: 'open-settings', map: BoardRead): void;
    (e: 'clone', map: BoardRead): void;
    (e: 'export', name: string): void;
    (e: 'delete', map: BoardRead): void;
}>();

const { t } = useI18n();
const auth = useAuthStore();
const capabilities = useCapabilitiesStore();

type SortCol = 'name' | 'type' | 'connection' | 'objects';

const COLUMNS: ReadonlyArray<{
    id: SortCol | 'actions';
    label: string;
    sortable: boolean;
    align?: 'right';
}> = [
    { id: 'name', label: 'home.colName', sortable: true },
    { id: 'type', label: 'home.colType', sortable: true },
    { id: 'connection', label: 'home.colConnection', sortable: true },
    { id: 'objects', label: 'home.colObjects', sortable: true, align: 'right' },
    { id: 'actions', label: 'home.colActions', sortable: false, align: 'right' },
];

// A non-admin may still hold edit rights on individual boards; show the actions
// column for them when at least one listed board is editable.
const anyEditable = computed(() => props.boards.some((b) => b.can_edit === true));

// Connection is admin-oriented; non-admins get a plain read-only list, plus
// the actions column only when they can edit some board.
const visibleColumns = computed(() => {
    if (auth.isAdmin) return COLUMNS;
    const hidden = anyEditable.value ? ['connection'] : ['connection', 'actions'];
    return COLUMNS.filter((c) => !hidden.includes(c.id));
});

const sortState = ref<{ col: SortCol | null; dir: 'asc' | 'desc' }>({
    col: null,
    dir: 'asc',
});

function setSort(col: SortCol | 'actions') {
    if (col === 'actions') return;
    if (sortState.value.col === col) {
        sortState.value.dir = sortState.value.dir === 'asc' ? 'desc' : 'asc';
    } else {
        sortState.value.col = col;
        sortState.value.dir = 'asc';
    }
}

function ariaSortFor(col: SortCol | 'actions'): 'ascending' | 'descending' | 'none' {
    if (sortState.value.col !== col) return 'none';
    return sortState.value.dir === 'asc' ? 'ascending' : 'descending';
}

function isDynamic(map: BoardRead): boolean {
    return Boolean(map.readonly) || ['flow', 'radar', 'worldmap'].includes(map.view.type);
}

function sortKey(map: BoardRead, col: SortCol): string | number {
    switch (col) {
        case 'name':
            return (map.alias || map.name).toLowerCase();
        case 'type':
            return map.view.type;
        case 'connection':
            return (map.connection_id || '').toLowerCase();
        case 'objects':
            return isDynamic(map) ? Number.MAX_SAFE_INTEGER : map.object_count;
    }
}

const sortedBoards = computed(() => {
    const list = props.boards;
    const col = sortState.value.col;
    if (!col) return list;
    const dir = sortState.value.dir === 'asc' ? 1 : -1;
    return [...list].sort((a, b) => {
        const av = sortKey(a, col);
        const bv = sortKey(b, col);
        if (av < bv) return -1 * dir;
        if (av > bv) return 1 * dir;
        return 0;
    });
});

const TYPE_LABELS: Record<string, string> = {
    static: 'Static',
    worldmap: 'Geo Board',
    flow: 'Flow Board',
    radar: 'Radar',
};
function boardTypeLabel(type: string) {
    return TYPE_LABELS[type] ?? type;
}

function typeBadgeClass(type: string): string {
    switch (type) {
        case 'worldmap':
            return 'bg-cyan-500/15 text-cyan-800 ring-1 ring-cyan-600/40 dark:bg-cyan-500/20 dark:text-cyan-300 dark:ring-cyan-500/30';
        case 'radar':
            return 'bg-violet-500/15 text-violet-800 ring-1 ring-violet-600/40 dark:bg-violet-500/20 dark:text-violet-300 dark:ring-violet-500/30';
        case 'flow':
            return 'bg-emerald-500/15 text-emerald-800 ring-1 ring-emerald-700/40 dark:bg-emerald-500/20 dark:text-emerald-300 dark:ring-emerald-500/30';
        case 'static':
            return 'bg-slate-500/15 text-slate-700 ring-1 ring-slate-500/40 dark:bg-slate-400/15 dark:text-slate-300 dark:ring-slate-400/30';
        default:
            return 'bg-[var(--bg-surface)] text-[var(--text)] ring-1 ring-[var(--default-border-color)]';
    }
}
</script>
