<template>
    <div class="orb-edit">
        <!-- Header -->
        <div class="orb-edit__header">
            <svg
                class="orb-edit__header-icon"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
            >
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            <div class="orb-edit__header-text">
                <div class="orb-edit__title">
                    {{ t('boardSettings.addObject') }}
                </div>
                <div class="orb-edit__hint" :class="{ 'orb-edit__hint--placing': placing }">
                    {{ placing ? t('boardSettings.clickToPlace') : t('boardSettings.dragObjects') }}
                </div>
            </div>
            <button
                class="orb-edit__close"
                :title="t('common.close')"
                :aria-label="t('common.close')"
                @click="$emit('cancel-add')"
            >
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

        <!-- Add Object form -->
        <div class="orb-edit__form">
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
                    :disabled="!loadingAddObjects && addObjects.length === 0"
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
                    class="orb-field"
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
                    class="orb-edit__aggr-chip"
                    :title="t('boardSettings.aggregationFunctionHint')"
                >
                    <span class="orb-edit__aggr-chip-label">
                        {{ t('boardSettings.aggregationFunction') }}
                    </span>
                    <span class="orb-edit__aggr-chip-value">{{ aggregationFunctionLabel }}</span>
                </div>
                <label class="orb-edit__depth-label">
                    {{ t('boardSettings.expandDepth') }}
                    <NumberInput
                        v-model="draft.expand_depth"
                        min="0"
                        max="10"
                        class="orb-edit__depth-input"
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
                    class="orb-edit__aggr-error"
                >
                    {{ t('boardSettings.aggregationPreviewConnectionDown') }}
                </div>
                <div v-else-if="aggregationPreview" class="orb-edit__aggr-preview">
                    <div class="orb-edit__aggr-preview-title">
                        {{ t('boardSettings.aggregationPreview') }}
                    </div>
                    <div class="orb-edit__aggr-counts">
                        <span
                            v-for="c in aggregationPreviewCounts"
                            :key="c.key"
                            class="orb-edit__aggr-count"
                            :style="{ color: c.count > 0 ? c.color : 'var(--text-muted)' }"
                        >
                            {{ c.label }}={{ c.count }}
                        </span>
                    </div>
                    <ul class="orb-edit__aggr-leaves">
                        <li
                            v-for="leaf in aggregationPreviewLeaves"
                            :key="leaf.id"
                            class="orb-edit__aggr-leaf"
                        >
                            <span class="orb-edit__aggr-dot" :style="{ background: leaf.color }" />
                            <span class="orb-edit__aggr-leaf-label">{{ leaf.label }}</span>
                        </li>
                        <li v-if="aggregationPreviewMore > 0" class="orb-edit__aggr-more">
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
                    <div v-if="aggregationPreviewDensityWarning" class="orb-edit__aggr-warning">
                        ⚠ {{ aggregationPreviewDensityWarning }}
                    </div>
                </div>
            </template>

            <template v-else-if="draft.type === 'dyngroup'">
                <select v-model="draft.object_types" class="orb-field">
                    <option value="host">host</option>
                    <option value="service">service</option>
                </select>
                <textarea
                    v-model="draft.object_filter"
                    class="orb-field orb-edit__code"
                    rows="3"
                    spellcheck="false"
                    placeholder="Filter: host_name ~ ^web\n"
                />
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
                    class="orb-field"
                />
            </template>

            <template v-else-if="draft.type === 'image'">
                <ImagePicker v-model="draft.image_src" />
                <input
                    v-model="draft.label_text"
                    :placeholder="t('boardSettings.labelOptional')"
                    class="orb-field"
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
                    class="orb-field orb-edit__code"
                />
            </template>

            <!-- Grid snap -->
            <div class="orb-edit__grid-row">
                <label class="orb-edit__grid-label">{{ t('boardSettings.grid') }}</label>
                <CmkDropdown
                    class="orb-edit__grid-select"
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
                :class="['orb-edit__place', placing ? 'orb-edit__place--pulsing' : '']"
                @click="canPlace && $emit('start-placing')"
            >
                {{ placing ? t('boardSettings.clickToPlace') : t('boardSettings.placeOnBoard') }}
            </CmkButton>
            <p v-if="draft.type && !canPlace && !placing" class="orb-edit__missing-hint">
                {{ missingFieldHint }}
            </p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi } from '@/api/client';
import CmkButton from '@/components/cmk/CmkButton';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import NumberInput from '@/components/NumberInput.vue';
import type { NewObjectDraft } from '@/composables/useBoardEditor';
import { useAuthStore } from '@/stores/auth';
import { useBoardsStore } from '@/stores/boards';
import { useSettingsStore } from '@/stores/settings';
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
    suggestions: placeableObjectTypes(t, settingsStore.system.enable_graph_objects),
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
const settingsStore = useSettingsStore();
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
        case 'dyngroup':
            return !!d.object_filter.trim();
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

watch(() => props.draft.type, onTypeChange, { immediate: true });

watch(
    () => props.draft.host_name,
    (host) => {
        if (props.draft.type === 'service' && host && addObjects.value.includes(host))
            fetchAddServices(host);
    },
);
</script>

<style scoped>
.orb-edit {
    display: flex;
    flex-direction: column;
    min-height: 0;
    font-size: var(--font-size-large);
    line-height: 20px;
}

.orb-edit__header {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
    flex-shrink: 0;
    padding: 10px var(--dimension-6);
    border-bottom: 1px solid color-mix(in srgb, white 8%, transparent);
}

.orb-edit__header-icon {
    flex-shrink: 0;
    width: 14px;
    height: 14px;
    color: var(--color-corporate-green-50);
}

.orb-edit__header-text {
    flex: 1;
    min-width: 0;
}

.orb-edit__title {
    font-size: var(--font-size-large);
    font-weight: 600;
    line-height: 20px;
    color: var(--text);
}

.orb-edit__hint {
    margin-top: var(--dimension-2);
    font-size: 10px;
    color: var(--text-muted);
}

.orb-edit__hint--placing {
    color: color-mix(in srgb, var(--color-yellow-50) 70%, transparent);
}

.orb-edit__close {
    flex-shrink: 0;
    padding: var(--dimension-3);
    color: var(--text-muted);
    border-radius: 6px;
    transition:
        color 0.15s,
        background-color 0.15s;
}

.orb-edit__close:hover {
    color: var(--text);
    background: var(--bg-hover);
}

.orb-edit__close svg {
    width: 14px;
    height: 14px;
}

.orb-edit__form {
    padding: 10px var(--dimension-6);
}

.orb-edit__form > :deep(* + *) {
    margin-top: var(--dimension-4);
}

.orb-edit__aggr-chip {
    display: inline-flex;
    align-items: center;
    align-self: flex-start;
    gap: 6px;
    padding: var(--dimension-2) var(--dimension-4);
    font-size: 10px;
    background: var(--bg-subtle, rgb(0 0 0 / 5%));
    border: 1px solid var(--border);
    border-radius: 9999px;
}

.orb-edit__aggr-chip-label {
    color: var(--text-muted);
}

.orb-edit__aggr-chip-value {
    font-family:
        ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
        monospace;
    color: var(--text);
}

.orb-edit__depth-label {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
    font-size: var(--font-size-normal);
    line-height: 16px;
    color: var(--text-muted);
}

.orb-edit :deep(.orb-edit__depth-input) {
    width: 64px;
}

.orb-edit__aggr-error {
    padding: var(--dimension-4);
    font-size: var(--font-size-normal);
    line-height: 16px;
    color: var(--color-light-red-10);
    background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-light-red-50) 40%, transparent);
    border-radius: 4px;
}

.orb-edit__aggr-preview {
    padding: var(--dimension-4);
    font-size: var(--font-size-normal);
    line-height: 16px;
    background: var(--bg-subtle, rgb(0 0 0 / 5%));
    border: 1px solid var(--border);
    border-radius: 4px;
}

.orb-edit__aggr-preview-title {
    margin-bottom: var(--dimension-3);
    color: var(--text-muted);
}

.orb-edit__aggr-counts {
    display: flex;
    gap: var(--dimension-5);
    margin-bottom: var(--dimension-3);
}

.orb-edit__aggr-count {
    font-family:
        ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
        monospace;
}

.orb-edit__aggr-leaves {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-2);
    margin: 0;
    padding: 0;
    list-style: none;
}

.orb-edit__aggr-leaf {
    display: flex;
    align-items: center;
    gap: var(--dimension-4);
    color: var(--text);
}

.orb-edit__aggr-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 9999px;
}

.orb-edit__aggr-leaf-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.orb-edit__aggr-more {
    font-style: italic;
    color: var(--text-muted);
}

.orb-edit__aggr-warning {
    margin-top: var(--dimension-4);
    padding: 6px;
    font-size: 10px;
    color: var(--color-yellow-50);
    background: color-mix(in srgb, var(--color-warning) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-warning) 40%, transparent);
    border-radius: 4px;
}

.orb-edit__code {
    font-family:
        ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
        monospace;
    font-size: var(--font-size-normal);
    line-height: 16px;
}

.orb-edit__grid-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--dimension-4);
}

.orb-edit__grid-label {
    font-size: var(--font-size-normal);
    line-height: 16px;
    color: var(--text-muted);
    user-select: none;
}

.orb-edit :deep(.orb-edit__grid-select) {
    width: 96px;
}

.orb-edit :deep(.orb-edit__place) {
    width: 100%;
}

.orb-edit :deep(.orb-edit__place--pulsing) {
    animation: orb-edit-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes orb-edit-pulse {
    50% {
        opacity: 0.5;
    }
}

.orb-edit__missing-hint {
    font-size: var(--font-size-normal);
    line-height: 16px;
    color: var(--text-muted);
    text-align: center;
}

/* Panel sits at the bottom of the viewport — force dropdowns to open upward */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-suggestions) {
    bottom: 100%;
    top: auto;
}
</style>
