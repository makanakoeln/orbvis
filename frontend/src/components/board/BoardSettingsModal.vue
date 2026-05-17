<template>
    <CmkSlideInDialog
        :open="true"
        :header="{ title: boardTitle, closeButton: true }"
        size="small"
        @close="requestClose"
    >
        <div class="board-settings__body">
            <!-- Tabs (only when there's more than one) -->
            <div v-if="tabs.length > 1" class="board-settings__tabs">
                <button
                    v-for="tab in tabs"
                    :key="tab.id"
                    type="button"
                    class="board-settings__tab"
                    :class="{ 'board-settings__tab--active': activeTab === tab.id }"
                    @click="activeTab = tab.id"
                >
                    {{ tab.label }}
                </button>
            </div>

            <div class="board-settings__scroll">
                <!-- General -->
                <div v-if="activeTab === 'general'" class="space-y-[10px]">
                    <!-- ID (read-only) — mirror ConnectionsView's "Connection ID"
                         field so both settings surfaces present the immutable
                         identifier the same way. The board name is the
                         filesystem-level key; renaming requires the explicit
                         "Clone" action. -->
                    <div class="space-y-[4px]">
                        <CmkLabel>{{ t('admin.boardId') }}</CmkLabel>
                        <p class="board-settings__id-readonly">{{ props.board.name }}</p>
                    </div>

                    <!-- Board type (read-only — switching type would invalidate type-specific
                         settings and the board geometry; cloning is the supported path).
                         Rendered as plain text (not Badge) so it doesn't suggest interaction. -->
                    <div class="space-y-[4px]">
                        <CmkLabel :help="t('board.boardTypeImmutable')">{{
                            t('board.boardType')
                        }}</CmkLabel>
                        <p class="board-settings__readonly-value">{{ boardTypeLabel }}</p>
                    </div>

                    <!-- Type-specific section first so the operator sees the
                         board's most distinctive controls (background image,
                         flow topology, radar filter, map view) right after the
                         ID header and before the generic FormSpec settings. -->

                    <!-- Background (static only) -->
                    <div
                        v-if="form.map_type === 'static'"
                        class="board-settings__type-section space-y-[8px]"
                    >
                        <p class="section-title">{{ t('boardSettings.background') }}</p>
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.backgroundImage') }}</CmkLabel>
                            <ImagePicker
                                v-model="form.background_image"
                                :placeholder="t('board.backgroundImagePlaceholder')"
                            />
                        </div>
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.backgroundColor') }}</CmkLabel>
                            <ColorInput
                                v-model="form.background_color"
                                :enable-label="t('common.useColor')"
                                default-color="#1f2937"
                            />
                        </div>
                    </div>

                    <!-- Worldmap settings -->
                    <template v-if="form.map_type === 'worldmap'">
                        <p class="section-title">{{ t('boardSettings.mapView') }}</p>
                        <div class="grid grid-cols-3 gap-[8px]">
                            <div class="space-y-[4px]">
                                <CmkLabel>{{ t('board.latitude') }}</CmkLabel>
                                <NumberInput
                                    v-model="form.worldmap_lat"
                                    step="any"
                                    :precision="10"
                                    class="w-full"
                                />
                            </div>
                            <div class="space-y-[4px]">
                                <CmkLabel>{{ t('board.longitude') }}</CmkLabel>
                                <NumberInput
                                    v-model="form.worldmap_lng"
                                    step="any"
                                    :precision="10"
                                    class="w-full"
                                />
                            </div>
                            <div class="space-y-[4px]">
                                <CmkLabel :help="t('board.worldmapHint')">{{
                                    t('board.zoom')
                                }}</CmkLabel>
                                <NumberInput
                                    v-model="form.worldmap_zoom"
                                    min="1"
                                    max="18"
                                    class="w-full"
                                />
                            </div>
                        </div>
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.tileUrl') }}</CmkLabel>
                            <CmkInput
                                v-model="form.worldmap_tile_url"
                                :placeholder="t('board.tileUrlPlaceholder')"
                                field-size="FILL"
                            />
                        </div>
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.tileSaturate') }}</CmkLabel>
                            <NumberInput
                                v-model="form.worldmap_tile_saturate"
                                :min="0"
                                :max="100"
                                :step="5"
                                :placeholder="t('board.tileSaturatePlaceholder')"
                                class="w-full"
                            />
                        </div>

                        <!-- Automap: dynamically populate the board from
                                 host geo-coords (orbvis_lat/orbvis_lng labels
                                 or LAT/LONG custom variables). Mirrors NagVis
                                 automap with lat/lng. -->
                        <div class="board-settings__subsection space-y-[4px]">
                            <CmkLabel :help="t('board.autoSourceHint')">{{
                                t('board.autoSource')
                            }}</CmkLabel>
                            <CmkDropdown
                                :selected-option="form.worldmap_auto_source || ''"
                                :options="worldmapAutoSourceOptions"
                                :width="'fill'"
                                :label="t('board.autoSource')"
                                @update:selected-option="
                                    form.worldmap_auto_source = ($event ??
                                        '') as typeof form.worldmap_auto_source
                                "
                            />
                            <CmkInput
                                v-if="
                                    form.worldmap_auto_source === 'hostgroup' ||
                                    form.worldmap_auto_source === 'servicegroup'
                                "
                                v-model="form.worldmap_auto_filter_value"
                                :placeholder="t('board.autoFilterValuePlaceholder')"
                                field-size="FILL"
                            />
                        </div>
                    </template>

                    <!-- Flow settings -->
                    <template v-if="form.map_type === 'flow'">
                        <p class="section-title">{{ t('boardSettings.topology') }}</p>
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.flowRoot') }}</CmkLabel>
                            <CmkInput
                                v-model="form.flow_root"
                                :placeholder="t('board.flowRootPlaceholder')"
                                field-size="FILL"
                            />
                        </div>
                        <div class="grid grid-cols-2 gap-[8px]">
                            <div class="space-y-[4px]">
                                <CmkLabel :help="t('board.flowHint')">{{
                                    t('board.flowChildLayers')
                                }}</CmkLabel>
                                <NumberInput
                                    v-model="form.flow_child_layers"
                                    :min="-1"
                                    :max="20"
                                    :placeholder="t('board.flowLayersPlaceholder')"
                                    class="w-full"
                                />
                            </div>
                            <div class="space-y-[4px]">
                                <CmkLabel :help="t('board.flowHint')">{{
                                    t('board.flowParentLayers')
                                }}</CmkLabel>
                                <NumberInput
                                    v-model="form.flow_parent_layers"
                                    :min="-1"
                                    :max="20"
                                    :placeholder="t('board.flowLayersPlaceholder')"
                                    class="w-full"
                                />
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-[8px]">
                            <div class="space-y-[4px]">
                                <CmkLabel :help="t('board.flowLimitsHint')">{{
                                    t('board.flowTopAffectedHosts')
                                }}</CmkLabel>
                                <NumberInput
                                    v-model="form.flow_top_affected_hosts"
                                    :min="0"
                                    :max="1000"
                                    :placeholder="String(FLOW_TOP_AFFECTED_HOSTS_DEFAULT)"
                                    class="w-full"
                                />
                            </div>
                            <div class="space-y-[4px]">
                                <CmkLabel :help="t('board.flowLimitsHint')">{{
                                    t('board.flowMaxServicesPerHost')
                                }}</CmkLabel>
                                <NumberInput
                                    v-model="form.flow_max_services_per_host"
                                    :min="0"
                                    :max="500"
                                    :placeholder="String(FLOW_MAX_SERVICES_PER_HOST_DEFAULT)"
                                    class="w-full"
                                />
                            </div>
                        </div>
                    </template>

                    <!-- Radar settings -->
                    <template v-if="form.map_type === 'radar'">
                        <p class="section-title">{{ t('boardSettings.radarFilter') }}</p>
                        <div class="grid grid-cols-2 gap-[8px]">
                            <div class="space-y-[4px]">
                                <CmkLabel>{{ t('board.filterType') }}</CmkLabel>
                                <CmkDropdown
                                    :selected-option="form.radar_filter || null"
                                    :options="radarFilterOptions"
                                    :width="'fill'"
                                    :label="t('board.filterType')"
                                    @update:selected-option="form.radar_filter = $event ?? ''"
                                />
                            </div>
                            <div
                                v-if="
                                    form.radar_filter === 'hostgroup' ||
                                    form.radar_filter === 'servicegroup'
                                "
                                class="space-y-[4px]"
                            >
                                <CmkLabel>{{ t('board.groupName') }}</CmkLabel>
                                <CmkInput
                                    v-model="form.radar_filter_value"
                                    placeholder="e.g. linux-servers"
                                    field-size="FILL"
                                />
                            </div>
                        </div>
                    </template>

                    <FormEdit
                        v-if="formSchema"
                        v-model:data="formSpecData"
                        :spec="formSchema"
                        :backend-validation="[]"
                    />
                    <CmkLoading v-else-if="schemaLoading" />

                    <p v-if="saveError" class="text-xs text-[var(--color-light-red-40)]">
                        {{ saveError }}
                    </p>
                </div>

                <!-- Permissions -->
                <div v-else-if="activeTab === 'permissions'">
                    <div v-if="permLoading" class="flex items-center justify-center py-8">
                        <CmkLoading />
                    </div>
                    <div v-else>
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="border-b border-[var(--border)]">
                                    <th
                                        class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                                        style="padding: var(--dimension-3) var(--dimension-4)"
                                    >
                                        {{ t('admin.role') }}
                                    </th>
                                    <th
                                        class="text-center text-sm font-semibold text-[var(--text-muted)] tracking-wider w-20"
                                        style="padding: var(--dimension-3) var(--dimension-4)"
                                    >
                                        {{ t('common.view') }}
                                    </th>
                                    <th
                                        class="text-center text-sm font-semibold text-[var(--text-muted)] tracking-wider w-20"
                                        style="padding: var(--dimension-3) var(--dimension-4)"
                                    >
                                        {{ t('common.edit') }}
                                    </th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-[var(--border)]">
                                <tr
                                    v-for="role in permRoles"
                                    :key="role.role_id"
                                    class="hover:bg-[var(--bg-hover)]"
                                >
                                    <td
                                        class="font-medium text-[var(--text)]"
                                        style="padding: var(--dimension-3) var(--dimension-4)"
                                    >
                                        {{ role.name }}
                                    </td>
                                    <td
                                        class="text-center"
                                        style="padding: var(--dimension-3) var(--dimension-4)"
                                    >
                                        <div class="flex items-center justify-center gap-[3px]">
                                            <CmkCheckbox
                                                :model-value="hasDraftPerm(role, 'view')"
                                                :disabled="hasWildcard(role, 'view')"
                                                @update:model-value="toggleDraftPerm(role, 'view')"
                                            />
                                            <span
                                                v-if="hasWildcard(role, 'view')"
                                                class="text-[10px] text-[var(--text-muted)]"
                                                :title="t('admin.viaWildcardRule')"
                                                >*</span
                                            >
                                        </div>
                                    </td>
                                    <td
                                        class="text-center"
                                        style="padding: var(--dimension-3) var(--dimension-4)"
                                    >
                                        <div class="flex items-center justify-center gap-[3px]">
                                            <CmkCheckbox
                                                :model-value="hasDraftPerm(role, 'edit')"
                                                :disabled="hasWildcard(role, 'edit')"
                                                @update:model-value="toggleDraftPerm(role, 'edit')"
                                            />
                                            <span
                                                v-if="hasWildcard(role, 'edit')"
                                                class="text-[10px] text-[var(--text-muted)]"
                                                :title="t('admin.viaWildcardRule')"
                                                >*</span
                                            >
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <p
                            v-if="!permRoles.length"
                            class="text-center py-6 text-[var(--text-muted)] text-sm"
                        >
                            {{ t('admin.noRoles') }}
                        </p>
                        <p class="text-sm text-[var(--text-muted)] mt-3 px-1">
                            * {{ t('admin.wildcardNote') }}
                        </p>
                    </div>
                </div>
            </div>

            <div class="board-settings__footer">
                <CmkButton variant="secondary" @click="requestClose">
                    {{ t('common.cancel') }}
                </CmkButton>
                <CmkButton variant="primary" :disabled="saving || !isDirty" @click="save">
                    {{ saving ? t('common.saving') : t('common.save') }}
                </CmkButton>
            </div>
        </div>
    </CmkSlideInDialog>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkSlideInDialog from '@cmk/components/CmkSlideInDialog.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import FormEdit from '@cmk/form/FormEdit.vue';
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch';
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError, boardsApi, boardsApiFormSpec, connectionsApi, rolesApi } from '@/api/client';
import ColorInput from '@/components/ColorInput.vue';
import NumberInput from '@/components/NumberInput.vue';
import { orbFormComponents } from '@/composables/orbFormComponents';
import { useAuthStore } from '@/stores/auth';
import type {
    BoardRead,
    ConnectionConfig,
    FlowView,
    PermissionRead,
    RadarView,
    RoleRead,
    WorldmapView,
} from '@/types/api';
import { boardTypeOptions } from '@/utils/dropdownOptions';

import ImagePicker from './ImagePicker.vue';

// Mirror of backend `Settings.flow_board_*` defaults — shown as placeholder so
// the user knows which value applies when the field is left empty.
const FLOW_TOP_AFFECTED_HOSTS_DEFAULT = 25;
const FLOW_MAX_SERVICES_PER_HOST_DEFAULT = 50;

const props = defineProps<{
    board: BoardRead;
    worldmapView?: { lat: number; lng: number; zoom: number } | null;
}>();
const emit = defineEmits<{ close: []; updated: [] }>();

const { t } = useI18n();
const auth = useAuthStore();

const tabs = computed<{ id: 'general' | 'permissions'; label: string }[]>(() => {
    const isCmk = auth.ssoActive || auth.isCheckmkDeployment;
    return [
        { id: 'general', label: t('admin.settings') },
        ...(!isCmk ? [{ id: 'permissions' as const, label: t('admin.boardPermissions') }] : []),
    ];
});
const activeTab = ref<'general' | 'permissions'>('general');

// ── General ────────────────────────────────────────────────────────────────

function initWorldmapCoords() {
    if (props.worldmapView) {
        return {
            lat: props.worldmapView.lat,
            lng: props.worldmapView.lng,
            zoom: props.worldmapView.zoom,
        };
    }
    if (props.board.view.type === 'worldmap') {
        const wv = props.board.view as WorldmapView;
        return { lat: wv.lat, lng: wv.lng, zoom: wv.zoom };
    }
    return { lat: 51.0, lng: 10.0, zoom: 5 };
}

const wm = initWorldmapCoords();
const rv = props.board.view.type === 'radar' ? (props.board.view as RadarView) : null;
const wmv = props.board.view.type === 'worldmap' ? (props.board.view as WorldmapView) : null;
const fv = props.board.view.type === 'flow' ? (props.board.view as FlowView) : null;

const form = ref({
    alias: props.board.alias,
    connection_id: props.board.connection_id,
    icon_size: props.board.icon_size,
    rotation_interval: props.board.rotation_interval,
    click_action: (props.board.click_action ?? 'link') as 'link' | 'none',
    show_in_lists: props.board.show_in_lists !== false,
    map_type: props.board.view.type,
    worldmap_auto_source: (wmv?.auto_source ?? '') as
        | ''
        | 'all_hosts'
        | 'hostgroup'
        | 'servicegroup',
    worldmap_auto_filter_value: wmv?.auto_filter_value ?? '',
    worldmap_lat: wm.lat,
    worldmap_lng: wm.lng,
    worldmap_zoom: wm.zoom,
    worldmap_tile_url: wmv?.tile_url ?? '',
    worldmap_tile_saturate: wmv?.tile_saturate ?? (null as number | null),
    radar_filter: rv?.filter ?? 'hostgroup',
    radar_filter_value: rv?.filter_value ?? '',
    flow_root: fv?.root ?? '',
    flow_child_layers: fv?.child_layers ?? (null as number | null),
    flow_parent_layers: fv?.parent_layers ?? (null as number | null),
    flow_top_affected_hosts: fv?.top_affected_hosts ?? (null as number | null),
    flow_max_services_per_host: fv?.max_services_per_host ?? (null as number | null),
    hover_template: props.board.hover_template ?? '',
    context_template: props.board.context_template ?? '',
    background_image: props.board.background_image ?? '',
    background_color: props.board.background_color ?? '',
});

const connections = ref<ConnectionConfig[]>([]);
const saving = ref(false);

type Schema = NonNullable<VueFormspecComponents['components']>;
initializeComponentRegistry(orbFormComponents);
const formSchema = ref<Schema | null>(null);
const schemaLoading = ref(true);
const formSpecData = ref<Record<string, unknown>>({
    alias: props.board.alias,
    connection_id: props.board.connection_id,
    icon_size: props.board.icon_size,
    rotation_interval: props.board.rotation_interval ?? 0,
    click_action: props.board.click_action ?? 'link',
    show_in_lists: props.board.show_in_lists !== false,
    hover_template: props.board.hover_template ?? '',
    context_template: props.board.context_template ?? '',
});

const boardTypeLabel = computed(
    () =>
        boardTypeOptions(t).find((o) => o.name === form.value.map_type)?.title ??
        form.value.map_type,
);

const boardTitle = computed(() => t('board.settingsTitle') + ' — ' + props.board.name);

const worldmapAutoSourceOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: '', title: t('board.autoSourceNone') },
        { name: 'all_hosts', title: t('board.autoSourceAllHosts') },
        { name: 'hostgroup', title: t('board.autoSourceHostgroup') },
        { name: 'servicegroup', title: t('board.autoSourceServicegroup') },
    ],
}));
const radarFilterOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: 'hostgroup', title: t('board.filterTypeHostgroup') },
        { name: 'servicegroup', title: t('board.filterTypeServicegroup') },
        { name: 'all_hosts', title: t('board.filterTypeAllHosts') },
        { name: 'all_services', title: t('board.filterTypeAllServices') },
    ],
}));
const saveError = ref('');

async function save() {
    saving.value = true;
    saveError.value = '';
    try {
        // Always save any pending permission changes
        if (permDraft.size > 0) {
            await savePermissions();
        }
        let view: Record<string, unknown>;
        if (form.value.map_type === 'worldmap') {
            view = {
                type: 'worldmap',
                lat: form.value.worldmap_lat,
                lng: form.value.worldmap_lng,
                zoom: form.value.worldmap_zoom,
                auto_source: form.value.worldmap_auto_source || null,
                auto_filter_value: form.value.worldmap_auto_filter_value,
                tile_url: form.value.worldmap_tile_url || null,
                tile_saturate: form.value.worldmap_tile_saturate,
            };
        } else if (form.value.map_type === 'radar') {
            view = {
                type: 'radar',
                filter: form.value.radar_filter,
                filter_value: form.value.radar_filter_value,
            };
        } else if (form.value.map_type === 'flow') {
            view = {
                type: 'flow',
                root: form.value.flow_root.trim() || null,
                child_layers: form.value.flow_child_layers,
                parent_layers: form.value.flow_parent_layers,
                top_affected_hosts: form.value.flow_top_affected_hosts,
                max_services_per_host: form.value.flow_max_services_per_host,
            };
        } else {
            view = { type: form.value.map_type };
        }
        const fs = formSpecData.value as Record<string, unknown>;
        await boardsApi.update(
            props.board.name,
            {
                alias: (fs.alias as string) ?? props.board.alias,
                connection_id: (fs.connection_id as string) ?? props.board.connection_id,
                icon_size: (fs.icon_size as number | null | undefined) ?? null,
                rotation_interval: (fs.rotation_interval as number | null | undefined) ?? 0,
                click_action: (fs.click_action as 'link' | 'none' | undefined) ?? 'link',
                show_in_lists: (fs.show_in_lists as boolean | undefined) ?? true,
                background_image: form.value.background_image || null,
                background_color: form.value.background_color || null,
                view,
                hover_template: ((fs.hover_template as string) ?? '') || null,
                context_template: ((fs.context_template as string) ?? '') || null,
            },
            auth.accessToken!,
            props.board.version ?? null,
        );
        emit('updated');
        emit('close');
    } catch (e: unknown) {
        // 409 means another operator saved this board after we opened it.
        // Surface a clear message instead of the generic "An error occurred"
        // so the operator can reload and reconcile.
        if (e instanceof ApiError && e.status === 409) {
            saveError.value = t('board.staleConflict');
        } else {
            saveError.value = e instanceof Error ? e.message : 'An error occurred';
        }
    } finally {
        saving.value = false;
    }
}

// ── Permissions ────────────────────────────────────────────────────────────
const permRoles = ref<RoleRead[]>([]);
const permLoading = ref(false);
// Draft: key = `${role_id}-${act}`, value = desired checked state (undefined = use server state)
const permDraft = reactive(new Map<string, boolean>());

// Snapshot the initial form state so we can disable Save when nothing
// changed and confirm before discarding edits on cancel/close.
const initialSnapshot = JSON.stringify({
    form: form.value,
    formSpec: formSpecData.value,
});
const isDirty = computed(
    () =>
        JSON.stringify({ form: form.value, formSpec: formSpecData.value }) !== initialSnapshot ||
        permDraft.size > 0,
);

function requestClose() {
    if (isDirty.value && !window.confirm(t('board.discardChangesConfirm'))) return;
    emit('close');
}

async function loadPermissions() {
    permLoading.value = true;
    try {
        permRoles.value = await rolesApi.list(auth.accessToken!);
        permDraft.clear();
    } finally {
        permLoading.value = false;
    }
}

function hasWildcard(role: RoleRead, act: string): boolean {
    return role.permissions.some((p) => p.mod === 'map' && p.act === act && p.obj === '*');
}

function hasDirectPerm(role: RoleRead, act: string): boolean {
    return role.permissions.some(
        (p) => p.mod === 'map' && p.act === act && p.obj === props.board.name,
    );
}

function hasDraftPerm(role: RoleRead, act: string): boolean {
    const key = `${role.role_id}-${act}`;
    if (permDraft.has(key)) return permDraft.get(key)!;
    return hasDirectPerm(role, act) || hasWildcard(role, act);
}

function toggleDraftPerm(role: RoleRead, act: string) {
    if (hasWildcard(role, act)) return;
    const key = `${role.role_id}-${act}`;
    const current = hasDraftPerm(role, act);
    permDraft.set(key, !current);
}

async function savePermissions() {
    for (const role of permRoles.value) {
        for (const act of ['view', 'edit'] as const) {
            if (hasWildcard(role, act)) continue;
            const key = `${role.role_id}-${act}`;
            if (!permDraft.has(key)) continue; // no change
            const desired = permDraft.get(key)!;
            const hasServer = hasDirectPerm(role, act);
            if (desired && !hasServer) {
                // add
                let existingPerm: PermissionRead | null = null;
                for (const r of permRoles.value) {
                    const p = r.permissions.find(
                        (p) => p.mod === 'map' && p.act === act && p.obj === props.board.name,
                    );
                    if (p) {
                        existingPerm = p;
                        break;
                    }
                }
                if (!existingPerm) {
                    existingPerm = await rolesApi.createPermission(
                        'map',
                        act,
                        props.board.name,
                        auth.accessToken!,
                    );
                }
                await rolesApi.assignPermission(
                    role.role_id,
                    existingPerm.perm_id,
                    auth.accessToken!,
                );
            } else if (!desired && hasServer) {
                // remove
                const perm = role.permissions.find(
                    (p) => p.mod === 'map' && p.act === act && p.obj === props.board.name,
                )!;
                await rolesApi.removePermission(role.role_id, perm.perm_id, auth.accessToken!);
            }
        }
    }
    permDraft.clear();
}

onMounted(async () => {
    const [bs, spec] = await Promise.all([
        connectionsApi.list(auth.accessToken!),
        boardsApiFormSpec.getMetadataSchema(auth.accessToken!).catch((): null => null),
        loadPermissions(),
    ]);
    connections.value = bs;
    schemaLoading.value = false;
    if (spec) formSchema.value = spec as unknown as Schema;
});
</script>

<style scoped>
@reference "tailwindcss";

.section-title {
    @apply text-xs font-semibold text-[var(--text-muted)] tracking-wider uppercase mb-[6px] leading-none;
}

.board-settings__body {
    display: flex;
    flex-direction: column;
    padding-bottom: var(--dimension-4);
}

/* Read-only display for unchangeable values (e.g. board type). Plain text
   on the form background so it doesn't suggest a button or pill. */
.board-settings__readonly-value {
    font-size: var(--font-size-normal);
    color: var(--text);
    margin: 0;
    padding: var(--dimension-1) 0;
}

.board-settings__id-readonly {
    font-family: var(--font-family-mono, monospace);
    font-size: 0.875rem;
    color: var(--text);
    padding: var(--dimension-3) var(--dimension-4);
    background: var(--bg-elevated, var(--bg-hover));
    border-radius: 6px;
    border: 1px solid var(--border);
    width: max-content;
    margin: 0;
}

/* Detail field that appears below a toggle, slightly indented and spaced so
   the operator sees the relationship at a glance. */
.board-settings__detail {
    margin-top: var(--dimension-2);
    margin-left: var(--dimension-5);
}

/* Section separator between logical clusters in the form. */
.board-settings__subsection {
    padding-top: var(--dimension-5);
    margin-top: var(--dimension-3);
    border-top: 1px solid var(--border);
}

.board-settings__tabs {
    display: flex;
    gap: var(--dimension-2);
    padding: 0 0 var(--dimension-4);
    border-bottom: 1px solid var(--border);
}

.board-settings__tab {
    padding: var(--dimension-2) var(--dimension-4);
    border-radius: var(--dimension-3);
    background: transparent;
    border: 0;
    font-size: var(--font-size-large);
    font-weight: 500;
    color: var(--text-muted);
    cursor: pointer;
}

.board-settings__tab:hover {
    color: var(--text);
    background: var(--bg-hover);
}

.board-settings__tab--active {
    background: rgb(21 209 160 / 20%);
    color: var(--color-corporate-green-40);
}

.board-settings__scroll {
    flex: 1;
    min-height: 0;
    padding-top: var(--dimension-5);
}

.board-settings__footer {
    position: sticky;
    bottom: 0;
    display: flex;
    justify-content: flex-end;
    gap: var(--dimension-3);
    padding: var(--dimension-4) 0;
    background: linear-gradient(
        to top,
        var(--bg-surface) 0%,
        var(--bg-surface) 75%,
        transparent 100%
    );
    margin-top: var(--dimension-5);
}
</style>
