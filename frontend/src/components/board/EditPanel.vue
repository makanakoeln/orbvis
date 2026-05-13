<template>
    <div class="flex flex-col min-h-0 text-sm">
        <!-- Header -->
        <div
            class="border-b border-white/8 flex items-center gap-[8px] shrink-0"
            style="padding: 10px 16px"
        >
            <svg
                class="text-[var(--color-corporate-green-50)] shrink-0"
                style="width: 14px; height: 14px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
            >
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            <div class="flex-1 min-w-0">
                <div class="font-semibold text-[var(--text)] text-sm">
                    {{ t('boardSettings.addObject') }}
                </div>
                <div
                    class="text-[10px] mt-[2px]"
                    :class="
                        placing ? 'text-[var(--color-yellow-50)]/70' : 'text-[var(--text-muted)]'
                    "
                >
                    {{ placing ? t('boardSettings.clickToPlace') : t('boardSettings.dragObjects') }}
                </div>
            </div>
            <button
                class="shrink-0 rounded-md p-[4px] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                :title="t('common.close')"
                :aria-label="t('common.close')"
                @click="$emit('cancel-add')"
            >
                <svg
                    style="width: 14px; height: 14px"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

        <!-- Add Object form -->
        <div class="space-y-[8px]" style="padding: 10px 16px">
            <CmkDropdown
                :selected-option="draft.type"
                :options="objectTypeOptions"
                :width="'fill'"
                :label="t('boardSettings.selectType')"
                @update:selected-option="(v) => (draft.type = v as ObjectType | '')"
            />

            <template v-if="draft.type === 'host'">
                <AutocompleteInput
                    v-model="draft.host_name"
                    :suggestions="addObjects"
                    :loading="loadingAddObjects"
                    :placeholder="t('boardSettings.hostname')"
                    :empty-text="t('boardSettings.noHosts')"
                />
            </template>

            <template v-else-if="draft.type === 'service'">
                <AutocompleteInput
                    v-model="draft.host_name"
                    :suggestions="addObjects"
                    :loading="loadingAddObjects"
                    :placeholder="t('boardSettings.hostname')"
                    :empty-text="t('boardSettings.noHosts')"
                    @change="onHostChange"
                />
                <AutocompleteInput
                    v-model="draft.service_description"
                    :suggestions="addServices"
                    :loading="loadingAddServices"
                    :placeholder="t('boardSettings.serviceDescription')"
                    :empty-text="
                        draft.host_name && !loadingAddServices
                            ? t('boardSettings.noServices')
                            : undefined
                    "
                />
            </template>

            <template v-else-if="draft.type === 'hostgroup' || draft.type === 'servicegroup'">
                <AutocompleteInput
                    v-model="draft.group_name"
                    :suggestions="addObjects"
                    :loading="loadingAddObjects"
                    :placeholder="t('boardSettings.groupName')"
                    :empty-text="
                        t(
                            draft.type === 'hostgroup'
                                ? 'boardSettings.noHostgroups'
                                : 'boardSettings.noServicegroups',
                        )
                    "
                />
            </template>

            <template v-else-if="draft.type === 'map'">
                <AutocompleteInput
                    v-model="draft.board_name"
                    :suggestions="boardNames"
                    :display-labels="boardLabels"
                    :loading="boardsStore.loading"
                    :placeholder="t('boardSettings.boardName')"
                    :empty-text="t('boardSettings.noBoards')"
                />
                <input
                    v-model="draft.label_text"
                    :placeholder="t('boardSettings.labelOptional')"
                    class="field"
                />
            </template>

            <template v-else-if="draft.type === 'aggregation'">
                <AutocompleteInput
                    v-model="draft.aggregation_id"
                    :suggestions="addAggregationIds"
                    :display-labels="addAggregationLabels"
                    :loading="loadingAddAggregations"
                    :placeholder="t('boardSettings.aggregationId')"
                    :empty-text="t('boardSettings.noAggregations')"
                />
                <!--
                    Read-only aggregation-function chip. Tells the designer
                    which top-level semantic the picked aggregation has
                    (worst / best / count_ok / state_of_host / ...) so
                    they don't have to crosscheck WATO. Hidden when the
                    function isn't available (no aggregation picked yet,
                    or cmk.bi didn't surface it on this CMK version).
                -->
                <div
                    v-if="aggregationFunctionLabel"
                    class="text-[10px] inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[var(--bg-subtle,rgba(0,0,0,0.05))] border border-[var(--border)] self-start"
                    :title="t('boardSettings.aggregationFunctionHint')"
                >
                    <span class="text-[var(--text-muted)]">
                        {{ t('boardSettings.aggregationFunction') }}
                    </span>
                    <span class="font-mono text-[var(--text)]">{{ aggregationFunctionLabel }}</span>
                </div>
                <label class="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                    {{ t('boardSettings.expandDepth') }}
                    <NumberInput
                        v-model="draft.expand_depth"
                        min="0"
                        max="10"
                        class="w-16"
                        :title="t('boardSettings.expandDepthHelp')"
                    />
                </label>
                <!--
                    Live preview of the resulting BI tree at the chosen depth.
                    Renders as a compact "{ok=N warn=N crit=N unkn=N} of M
                    leaves" line plus the first few leaves so the designer
                    sees the fan-out before saving. The render shape (counts +
                    sample) is deliberately minimal — fully expanded trees
                    can fan out to hundreds of nodes which would slow down
                    re-renders during typing.
                -->
                <!--
                    When the connection probe fails, render a distinct
                    "preview unavailable" hint instead of silently hiding
                    the panel. Otherwise the designer can't tell whether
                    the aggregation legitimately has 0 leaves or whether
                    the livestatus connection is down.
                -->
                <div
                    v-if="!aggregationConnectionOk && draft.aggregation_id && !aggregationPreview"
                    class="text-xs rounded p-2 border border-rose-500/40 bg-rose-500/10 text-rose-200"
                >
                    {{ t('boardSettings.aggregationPreviewConnectionDown') }}
                </div>
                <div
                    v-else-if="aggregationPreview"
                    class="text-xs rounded p-2 bg-[var(--bg-subtle,rgba(0,0,0,0.05))] border border-[var(--border)]"
                >
                    <div class="text-[var(--text-muted)] mb-1">
                        {{ t('boardSettings.aggregationPreview') }}
                    </div>
                    <div class="flex gap-3 mb-1">
                        <span
                            v-for="c in aggregationPreviewCounts"
                            :key="c.key"
                            class="font-mono"
                            :style="{ color: c.count > 0 ? c.color : 'var(--text-muted)' }"
                        >
                            {{ c.label }}={{ c.count }}
                        </span>
                    </div>
                    <ul class="m-0 p-0 list-none flex flex-col gap-0.5">
                        <li
                            v-for="leaf in aggregationPreviewLeaves"
                            :key="leaf.id"
                            class="flex items-center gap-2 text-[var(--text)]"
                        >
                            <span
                                class="inline-block w-1.5 h-1.5 rounded-full"
                                :style="{ background: leaf.color }"
                            />
                            <span class="truncate">{{ leaf.label }}</span>
                        </li>
                        <li
                            v-if="aggregationPreviewMore > 0"
                            class="text-[var(--text-muted)] italic"
                        >
                            …{{
                                t('boardSettings.aggregationPreviewMore', {
                                    count: aggregationPreviewMore,
                                })
                            }}
                        </li>
                    </ul>
                    <!--
                        Density warning: an aggregation with expand_depth >0
                        and >50 leaves renders dozens of state-coloured
                        circles next to the root glyph and easily clutters
                        worldmap/static boards. Suggest dropping expand_depth
                        to 0 (drawer-only viewing) when this happens. Threshold
                        is empirical — most multi-host aggregations fan to
                        20-40, so 50 is the comfortable cutoff.
                    -->
                    <div
                        v-if="aggregationPreviewDensityWarning"
                        class="mt-2 rounded p-1.5 text-[10px] border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 text-[var(--color-yellow-50)]"
                    >
                        ⚠ {{ aggregationPreviewDensityWarning }}
                    </div>
                </div>
            </template>

            <template v-else-if="draft.type === 'line'">
                <AutocompleteInput
                    v-model="draft.host_name"
                    :suggestions="addObjects"
                    :loading="loadingAddObjects"
                    :placeholder="t('boardSettings.hostname') + ' (optional)'"
                    :empty-text="t('boardSettings.noHosts')"
                    @change="onHostChange"
                />
                <AutocompleteInput
                    v-model="draft.service_description"
                    :suggestions="addServices"
                    :loading="loadingAddServices"
                    :placeholder="t('boardSettings.serviceOptional')"
                />
            </template>

            <template v-else-if="draft.type === 'textbox'">
                <input
                    v-model="draft.label_text"
                    :placeholder="t('boardSettings.textContent')"
                    class="field"
                />
            </template>

            <template v-else-if="draft.type === 'image'">
                <ImagePicker v-model="draft.image_src" />
                <input
                    v-model="draft.label_text"
                    :placeholder="t('boardSettings.labelOptional')"
                    class="field"
                />
            </template>

            <template v-else-if="draft.type === 'graph'">
                <AutocompleteInput
                    v-model="draft.host_name"
                    :suggestions="addObjects"
                    :loading="loadingAddObjects"
                    :placeholder="t('boardSettings.hostname')"
                    :empty-text="t('boardSettings.noHosts')"
                    @change="onHostChange"
                />
                <AutocompleteInput
                    v-model="draft.service_description"
                    :suggestions="addServices"
                    :loading="loadingAddServices"
                    :placeholder="t('boardSettings.serviceOptional')"
                />
                <input
                    v-model="draft.graph_url"
                    :placeholder="t('boardSettings.graphUrl') + ' (optional)'"
                    class="field font-mono text-xs"
                />
            </template>

            <!-- Grid snap -->
            <div class="flex items-center justify-between gap-[8px]">
                <label class="text-xs text-[var(--text-muted)] select-none">{{
                    t('boardSettings.grid')
                }}</label>
                <CmkDropdown
                    class="w-[96px]"
                    :selected-option="String(snapGrid)"
                    :options="snapGridOptions"
                    label=""
                    @update:selected-option="(v) => $emit('update:snapGrid', Number(v))"
                />
            </div>

            <CmkButton
                v-if="draft.type"
                :variant="placing ? 'warning' : 'primary'"
                :disabled="!canPlace"
                :class="['w-full', placing ? 'animate-pulse' : '']"
                @click="canPlace && $emit('start-placing')"
            >
                {{ placing ? t('boardSettings.clickToPlace') : t('boardSettings.placeOnBoard') }}
            </CmkButton>
            <p
                v-if="draft.type && !canPlace && !placing"
                class="text-xs text-[var(--text-muted)] text-center"
            >
                {{ missingFieldHint }}
            </p>
        </div>
    </div>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi } from '@/api/client';
import NumberInput from '@/components/NumberInput.vue';
import type { NewObjectDraft } from '@/composables/useBoardEditor';
import { useAuthStore } from '@/stores/auth';
import { useBoardsStore } from '@/stores/boards';
import type { AggregationNode, ObjectType } from '@/types/api';
import {
    aggregationLeafId,
    BI_STATE_COLOR,
    BI_STATE_LABEL,
    countLeavesByState,
    flattenAggregationLeaves,
} from '@/utils/aggregationTree';
import { placeableObjectTypes } from '@/utils/dropdownOptions';

import AutocompleteInput from './AutocompleteInput.vue';
import ImagePicker from './ImagePicker.vue';

const { t } = useI18n();

const objectTypeOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [{ name: '', title: t('boardSettings.selectType') }, ...placeableObjectTypes(t)],
}));
const snapGridOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: '0', title: t('boardSettings.gridOff') },
        { name: '10', title: '10 px' },
        { name: '20', title: '20 px' },
        { name: '50', title: '50 px' },
    ],
}));

const props = defineProps<{
    draft: NewObjectDraft;
    placing: boolean;
    connectionId: string;
    snapGrid: number;
}>();

defineEmits<{
    'start-placing': [];
    'update:snapGrid': [value: number];
    'cancel-add': [];
}>();

const auth = useAuthStore();
const boardsStore = useBoardsStore();
const boardNames = computed(() => boardsStore.boards.map((b) => b.name));
const boardLabels = computed(() => boardsStore.boards.map((b) => b.alias || b.name));

const MISSING_FIELD_KEY: Record<string, string> = {
    host: 'boardSettings.hostname',
    hostgroup: 'boardSettings.groupName',
    servicegroup: 'boardSettings.groupName',
    map: 'boardSettings.boardName',
    aggregation: 'boardSettings.aggregationId',
};

const canPlace = computed(() => {
    const d = props.draft;
    switch (d.type) {
        case 'host':
            return !!d.host_name;
        case 'service':
            return !!d.host_name && !!d.service_description;
        case 'hostgroup':
        case 'servicegroup':
            return !!d.group_name;
        case 'map':
            return !!d.board_name;
        case 'aggregation':
            return !!d.aggregation_id;
        case 'line':
        case 'textbox':
        case 'image':
        case 'graph':
            return true;
        default:
            return false;
    }
});

const missingFieldHint = computed(() => {
    if (canPlace.value) return '';
    const d = props.draft;
    if (d.type === 'service')
        return `↑ ${t(d.host_name ? 'boardSettings.serviceDescription' : 'boardSettings.hostname')}`;
    return MISSING_FIELD_KEY[d.type] ? `↑ ${t(MISSING_FIELD_KEY[d.type])}` : '';
});

const addObjects = ref<string[]>([]);
const addServices = ref<string[]>([]);
const addAggregationIds = ref<string[]>([]);
const addAggregationLabels = ref<string[]>([]);
// Map of aggregation id → top-level function (e.g. "worst", "best").
// Populated from the same /connections/<id>/aggregations response that
// drives the autocomplete; consumed by the read-only chip in the
// EditPanel's aggregation block.
const aggregationFunctions = ref<Record<string, string>>({});
const loadingAddObjects = ref(false);
const loadingAddServices = ref(false);
const loadingAddAggregations = ref(false);

async function fetchAddObjects(type: string) {
    if (
        !props.connectionId ||
        !type ||
        type === 'line' ||
        type === 'textbox' ||
        type === 'map' ||
        type === 'image'
    ) {
        addObjects.value = [];
        return;
    }
    loadingAddObjects.value = true;
    try {
        addObjects.value = await connectionsApi.objects(
            props.connectionId,
            type,
            auth.accessToken!,
        );
    } catch {
        addObjects.value = [];
    } finally {
        loadingAddObjects.value = false;
    }
}

async function fetchAddServices(host: string) {
    if (!host || !props.connectionId) {
        addServices.value = [];
        return;
    }
    loadingAddServices.value = true;
    try {
        addServices.value = await connectionsApi.objects(
            props.connectionId,
            'service',
            auth.accessToken!,
            host,
        );
    } catch {
        addServices.value = [];
    } finally {
        loadingAddServices.value = false;
    }
}

async function fetchAddAggregations() {
    if (!props.connectionId) {
        addAggregationIds.value = [];
        addAggregationLabels.value = [];
        aggregationFunctions.value = {};
        return;
    }
    loadingAddAggregations.value = true;
    try {
        const aggrs = await connectionsApi.aggregations(props.connectionId, auth.accessToken!);
        addAggregationIds.value = aggrs.map((a) => a.id);
        addAggregationLabels.value = aggrs.map((a) => a.title || a.id);
        const fnMap: Record<string, string> = {};
        for (const a of aggrs) {
            if (a.function) fnMap[a.id] = a.function;
        }
        aggregationFunctions.value = fnMap;
    } catch {
        addAggregationIds.value = [];
        addAggregationLabels.value = [];
        aggregationFunctions.value = {};
    } finally {
        loadingAddAggregations.value = false;
    }
}

const aggregationFunctionLabel = computed<string | null>(() => {
    const id = props.draft.aggregation_id;
    if (!id) return null;
    return aggregationFunctions.value[id] ?? null;
});

const aggregationPreview = ref<AggregationNode | null>(null);
const aggregationConnectionOk = ref<boolean>(true);

const aggregationPreviewLeavesAll = computed<AggregationNode[]>(() =>
    aggregationPreview.value ? flattenAggregationLeaves(aggregationPreview.value) : [],
);

const aggregationPreviewCounts = computed(() => {
    const counts = countLeavesByState(aggregationPreviewLeavesAll.value);
    return [2, 1, 3, 0].map((s) => ({
        key: String(s),
        label: BI_STATE_LABEL[s],
        color: BI_STATE_COLOR[s],
        count: counts[s] ?? 0,
    }));
});

const aggregationPreviewLeaves = computed(() =>
    aggregationPreviewLeavesAll.value.slice(0, 5).map((l) => ({
        id: aggregationLeafId(l),
        label: l.name,
        color: BI_STATE_COLOR[l.state] ?? BI_STATE_COLOR[3],
    })),
);

const aggregationPreviewMore = computed(() =>
    Math.max(0, aggregationPreviewLeavesAll.value.length - 5),
);

const _DENSITY_WARN_THRESHOLD = 50;
const aggregationPreviewDensityWarning = computed<string | null>(() => {
    const total = aggregationPreviewLeavesAll.value.length;
    const depth = props.draft.expand_depth ?? 0;
    if (depth > 0 && total > _DENSITY_WARN_THRESHOLD) {
        return t('boardSettings.aggregationDensityWarning', { count: total });
    }
    return null;
});

let _aggregationPreviewToken = 0;
async function refreshAggregationPreview(): Promise<void> {
    const id = props.draft.aggregation_id;
    const depth = Math.max(1, props.draft.expand_depth ?? 1);
    if (!props.connectionId || !id) {
        aggregationPreview.value = null;
        aggregationConnectionOk.value = true;
        return;
    }
    const myToken = ++_aggregationPreviewToken;
    try {
        const result = await connectionsApi.aggregationTree(
            props.connectionId,
            id,
            depth,
            auth.accessToken!,
        );
        // Only commit if this is the latest pending request — protects
        // against flicker when the operator changes the input quickly.
        if (myToken === _aggregationPreviewToken) {
            aggregationPreview.value = result.tree;
            aggregationConnectionOk.value = result.connection_ok;
        }
    } catch {
        if (myToken === _aggregationPreviewToken) {
            aggregationPreview.value = null;
            aggregationConnectionOk.value = false;
        }
    }
}

watch(
    () => [props.draft.aggregation_id, props.draft.expand_depth, props.connectionId] as const,
    () => {
        if (props.draft.type === 'aggregation') void refreshAggregationPreview();
    },
    { immediate: true },
);

function onTypeChange() {
    props.draft.host_name = '';
    props.draft.service_description = '';
    props.draft.group_name = '';
    props.draft.board_name = '';
    props.draft.aggregation_id = '';
    props.draft.expand_depth = 0;
    props.draft.label_text = '';
    props.draft.image_src = '';
    props.draft.graph_url = '';
    addObjects.value = [];
    addServices.value = [];
    if (props.draft.type === 'map') {
        if (boardsStore.boards.length === 0) boardsStore.fetchBoards();
        return;
    }
    if (props.draft.type === 'aggregation') {
        fetchAddAggregations();
        return;
    }
    const fetchType =
        props.draft.type === 'service' ||
        props.draft.type === 'line' ||
        props.draft.type === 'graph'
            ? 'host'
            : props.draft.type;
    fetchAddObjects(fetchType);
}

function onHostChange() {
    fetchAddServices(props.draft.host_name);
}

watch(() => props.draft.type, onTypeChange);

watch(
    () => props.draft.host_name,
    (host) => {
        if (props.draft.type === 'service' && host && addObjects.value.includes(host))
            fetchAddServices(host);
    },
);
</script>

<style scoped>
@reference "tailwindcss";

.field {
    @apply w-full bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-[var(--text)] placeholder-[var(--default-form-element-placeholder-color)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)] transition-all duration-150;

    padding: 5px 10px;
}

/* Panel sits at the bottom of the viewport — force dropdowns to open upward */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-suggestions) {
    bottom: 100%;
    top: auto;
}
</style>
