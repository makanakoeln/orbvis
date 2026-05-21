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

            <div ref="scrollEl" class="board-settings__scroll">
                <!-- General -->
                <div v-if="activeTab === 'general'" class="space-y-[10px]">
                    <!-- ID + Board type as a compact chip row. Both are
                         read-only — switching either would invalidate
                         per-type settings and the filesystem key; cloning is
                         the supported rename/conversion path. -->
                    <div class="board-settings__id-row">
                        <span class="board-settings__id-chip">{{ props.board.name }}</span>
                        <details
                            ref="typeMenuEl"
                            class="board-settings__type-chip-menu"
                            :title="t('board.boardTypeImmutable')"
                        >
                            <summary class="board-settings__type-chip">
                                {{ boardTypeLabel }}
                                <span aria-hidden="true">▾</span>
                            </summary>
                            <div class="board-settings__type-chip-actions">
                                <button
                                    type="button"
                                    class="board-settings__type-chip-action"
                                    @click="quickClone"
                                >
                                    {{ t('admin.cloneBoardAction') }}
                                </button>
                                <button
                                    type="button"
                                    class="board-settings__type-chip-action"
                                    @click="quickExport"
                                >
                                    {{ t('board.exportBoardAction') }}
                                </button>
                            </div>
                        </details>
                    </div>

                    <!-- Section jump-nav so the operator can skip past long
                         FormSpec groups without scrolling the whole form. -->
                    <nav
                        v-if="sectionNav.length > 1"
                        class="board-settings__section-nav"
                        :aria-label="t('boardSettings.sectionNav')"
                    >
                        <CmkButton
                            v-for="s in sectionNav"
                            :key="s.key"
                            variant="optional"
                            @click="scrollToSection(s.key)"
                        >
                            {{ s.label }}
                        </CmkButton>
                    </nav>

                    <!-- Generic metadata (Identification, Display, Behavior,
                         Templates) renders first so the operator can name and
                         wire up the board before tuning type-specific
                         topology / map view / filter blocks below. -->
                    <FormEdit
                        v-if="formSchema"
                        v-model:data="formSpecData"
                        :spec="formSchema"
                        :backend-validation="formBackendValidation"
                    />
                    <CmkLoading v-else-if="schemaLoading" />

                    <!-- Background (static only) -->
                    <div
                        v-if="form.map_type === 'static'"
                        data-section="background"
                        class="board-settings__type-section space-y-[8px]"
                    >
                        <p class="section-title">{{ t('boardSettings.background') }}</p>
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.backgroundImage') }}</CmkLabel>
                            <BackgroundImageUpload
                                v-model="form.background_image"
                                :board-name="props.board.name"
                                @replaced="bgReplaced = true"
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
                    <div
                        v-if="form.map_type === 'worldmap'"
                        data-section="mapview"
                        class="board-settings__type-section space-y-[8px]"
                    >
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
                            <div
                                v-if="
                                    form.worldmap_auto_source === 'hostgroup' ||
                                    form.worldmap_auto_source === 'servicegroup'
                                "
                                class="space-y-[4px]"
                            >
                                <CmkLabel>
                                    {{ t('board.groupName') }}<CmkLabelRequired space="before" />
                                </CmkLabel>
                                <CmkInput
                                    v-model="form.worldmap_auto_filter_value"
                                    :placeholder="t('board.autoFilterValuePlaceholder')"
                                    field-size="FILL"
                                    :class="{
                                        'orb-input-invalid':
                                            saveAttempted && !form.worldmap_auto_filter_value,
                                    }"
                                />
                            </div>
                        </div>
                    </div>

                    <!-- Flow settings: served as a FormSpec so titles/help
                         and the Integer-input look match the rest of the
                         Checkmk FormSpec UI. -->
                    <div v-if="form.map_type === 'flow'" data-section="topology">
                        <FormEdit
                            v-if="flowViewFormSchema"
                            v-model:data="flowViewFormSpecData"
                            :spec="flowViewFormSchema"
                            :backend-validation="[]"
                        />
                    </div>

                    <!-- Radar settings -->
                    <div
                        v-if="form.map_type === 'radar'"
                        data-section="radarFilter"
                        class="board-settings__type-section space-y-[8px]"
                    >
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
                                <CmkDropdown
                                    :selected-option="form.radar_filter_value || null"
                                    :options="radarGroupOptions"
                                    :width="'fill'"
                                    :label="t('board.groupName')"
                                    :input-hint="t('boardSettings.groupName')"
                                    :required="true"
                                    :form-validation="saveAttempted && !form.radar_filter_value"
                                    :no-elements-text="
                                        t(
                                            form.radar_filter === 'hostgroup'
                                                ? 'boardSettings.noHostgroups'
                                                : 'boardSettings.noServicegroups',
                                        )
                                    "
                                    @update:selected-option="form.radar_filter_value = $event ?? ''"
                                />
                            </div>
                        </div>
                    </div>

                    <ul
                        v-if="errorMessages.length"
                        class="text-xs text-[var(--color-light-red-40)] space-y-0.5"
                    >
                        <li v-for="(msg, i) in errorMessages" :key="i">{{ msg }}</li>
                    </ul>

                    <!-- Danger zone — keep deletion accessible without
                         leaving the settings dialog. Collapsed by default so
                         it doesn't compete with the normal Save/Cancel flow. -->
                    <details class="board-settings__danger-zone">
                        <summary class="board-settings__danger-zone-summary">
                            {{ t('board.dangerZone') }}
                        </summary>
                        <div class="board-settings__danger-zone-body">
                            <p class="text-sm text-[var(--text-muted)]">
                                {{ t('board.deleteBoardHint') }}
                            </p>
                            <CmkButton variant="danger" @click="deleteBoard">
                                {{ t('board.deleteBoardAction') }}
                            </CmkButton>
                        </div>
                    </details>
                </div>

                <!-- Permissions -->
                <div v-else-if="activeTab === 'permissions'">
                    <!-- Inside a Checkmk deployment, board view/edit is gated
                         by the CMK role permissions (orbvis.see, orbvis.edit).
                         The OrbVis role table is not the source of truth here,
                         so we show a read-only summary and deep-link instead
                         of letting the operator edit a copy that doesn't
                         apply. -->
                    <div v-if="isCmkDeployment" class="space-y-4">
                        <p class="text-sm text-[var(--text)]">
                            {{ t('board.permissionsCmkIntro') }}
                        </p>
                        <CmkButton variant="secondary" @click="openCmkRoles">
                            {{ t('board.permissionsCmkOpen') }}
                        </CmkButton>
                    </div>
                    <div v-else-if="permLoading" class="flex items-center justify-center py-8">
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
                <CmkButton
                    variant="optional"
                    :disabled="!isDirty || saving"
                    :title="isDirty ? undefined : t('board.resetDisabledClean')"
                    @click="resetChanges"
                >
                    {{ t('board.resetChanges') }}
                </CmkButton>
                <span class="board-settings__footer-meta">
                    {{ t('board.versionLabel', { version: props.board.version ?? 0 }) }}
                    <span class="board-settings__footer-shortcut">{{ saveShortcutHint }}</span>
                </span>
                <CmkButton variant="secondary" @click="requestClose">
                    {{ t('common.cancel') }}
                </CmkButton>
                <CmkButton
                    variant="primary"
                    :disabled="saving || !isDirty || (saveAttempted && !customSectionValid)"
                    :title="saveButtonTitle || undefined"
                    @click="save"
                >
                    {{ saving ? t('common.saving') : t('common.save') }}
                </CmkButton>
            </div>
        </div>
    </CmkSlideInDialog>
</template>

<script setup lang="ts">
import CmkLabelRequired from '@cmk/components/user-input/CmkLabelRequired.vue';
import FormEdit from '@cmk/form/FormEdit.vue';
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch';
import type {
    ValidationMessage,
    VueFormspecComponents,
} from 'cmk-shared-typing/typescript/vue_formspec_components';
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError, boardsApi, boardsApiFormSpec, connectionsApi, rolesApi } from '@/api/client';
import CmkButton from '@/components/cmk/CmkButton';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import CmkLabel from '@/components/cmk/CmkLabel';
import CmkLoading from '@/components/cmk/CmkLoading';
import CmkSlideInDialog from '@/components/cmk/CmkSlideInDialog';
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import ColorInput from '@/components/ColorInput.vue';
import NumberInput from '@/components/NumberInput.vue';
import { orbFormComponents } from '@/composables/orbFormComponents';
import { useRadarGroups } from '@/composables/useRadarGroups';
import { useToast } from '@/composables/useToast';
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
import { openUrl } from '@/utils/boardNavigation';
import { boardTypeOptions } from '@/utils/dropdownOptions';
import { toFormValidation } from '@/utils/formValidation';

import BackgroundImageUpload from './BackgroundImageUpload.vue';

const props = defineProps<{
    board: BoardRead;
    worldmapView?: { lat: number; lng: number; zoom: number } | null;
}>();
const emit = defineEmits<{ close: []; updated: []; clone: [name: string] }>();

const { t } = useI18n();
const auth = useAuthStore();
const toast = useToast();

const isCmkDeployment = computed(() => auth.ssoActive || auth.isCheckmkDeployment);

// Expose the current connection id so custom FormSpec widgets (in
// particular FormOrbHostAutocomplete) can pull suggestions from the
// matching backend without re-discovering it from the props.
const currentConnectionId = computed(
    () => (formSpecData.value.connection_id as string | undefined) ?? props.board.connection_id,
);
provide('orbConnectionId', currentConnectionId);
const tabs = computed<{ id: 'general' | 'permissions'; label: string }[]>(() => [
    { id: 'general', label: t('admin.settings') },
    { id: 'permissions', label: t('admin.boardPermissions') },
]);
const activeTab = ref<'general' | 'permissions'>('general');

// CMK roles editor — same OMD site as the OrbVis path prefix; matches
// the regex used in stores/auth.ts for the logout URL.
const cmkRolesUrl = computed(() => {
    const m = window.location.pathname.match(/^(\/[^/]+)\/orbvis/);
    return m ? `${m[1]}/check_mk/wato.py?mode=roles` : '/check_mk/wato.py?mode=roles';
});

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
// Optional fields are omitted entirely when the board has no value, so the
// FormSpec dispatcher renders them as un-checked (= inherit global defaults);
// '' / null would leave the checkbox enabled with an empty value, which reads
// as "override with nothing".
// click_action is a BooleanChoice in the FormSpec but 'link'|'none' on the
// wire; rotation_interval is a CascadingSingleChoice but a flat int on the
// wire. Both are flattened on save() below.
const rotationInterval = props.board.rotation_interval ?? 0;
const formSpecDataInitial: Record<string, unknown> = {
    alias: props.board.alias,
    connection_id: props.board.connection_id,
    rotation_interval: rotationInterval > 0 ? ['every', rotationInterval] : ['off', null],
    click_action: props.board.click_action !== 'none',
    show_in_lists: props.board.show_in_lists !== false,
};
if (props.board.icon_size != null) formSpecDataInitial.icon_size = props.board.icon_size;
if (props.board.hover_template) formSpecDataInitial.hover_template = props.board.hover_template;
if (props.board.context_template)
    formSpecDataInitial.context_template = props.board.context_template;
const formSpecData = ref<Record<string, unknown>>(formSpecDataInitial);

// Separate FormSpec data bag for the Flow `view` block. Same omit-when-null
// convention as the metadata schema: a missing key reads as "inherit", which
// matches FlowView's `None = use default` semantics.
const flowViewFormSpecDataInitial: Record<string, unknown> = {};
if (fv?.root) flowViewFormSpecDataInitial.root = fv.root;
if (fv?.child_layers != null) flowViewFormSpecDataInitial.child_layers = fv.child_layers;
if (fv?.parent_layers != null) flowViewFormSpecDataInitial.parent_layers = fv.parent_layers;
if (fv?.top_affected_hosts != null)
    flowViewFormSpecDataInitial.top_affected_hosts = fv.top_affected_hosts;
if (fv?.max_services_per_host != null)
    flowViewFormSpecDataInitial.max_services_per_host = fv.max_services_per_host;
const flowViewFormSpecData = ref<Record<string, unknown>>(flowViewFormSpecDataInitial);
const flowViewFormSchema = ref<Schema | null>(null);

const boardTypeLabel = computed(
    () =>
        boardTypeOptions(t).find((o) => o.name === form.value.map_type)?.title ??
        form.value.map_type,
);

// Header shows the human-readable alias; the technical slug stays
// visible as a small chip inside the modal body for operators who need
// to script against it.
const boardTitle = computed(
    () => t('board.settingsTitle') + ' — ' + (form.value.alias || props.board.name),
);

// Section jump-nav. Keys must match FormDictionary's `data-group` (from
// OrbDictGroup.key) for FormSpec sections, or `data-section` for the
// custom Vue sections (background/mapview/radarFilter).
const sectionNav = computed<{ key: string; label: string }[]>(() => {
    const nav = [
        { key: 'identification', label: t('boardSettings.identification') },
        { key: 'display', label: t('boardSettings.displayDefaults') },
        { key: 'behavior', label: t('boardSettings.behavior') },
        { key: 'templates', label: t('boardSettings.templates') },
    ];
    if (form.value.map_type === 'static') {
        nav.push({ key: 'background', label: t('boardSettings.background') });
    } else if (form.value.map_type === 'worldmap') {
        nav.push({ key: 'mapview', label: t('boardSettings.mapView') });
    } else if (form.value.map_type === 'radar') {
        nav.push({ key: 'radarFilter', label: t('boardSettings.radarFilter') });
    } else if (form.value.map_type === 'flow') {
        nav.push({ key: 'topology', label: t('boardSettings.hostsAndLayer') });
    }
    return nav;
});

const scrollEl = ref<HTMLElement | null>(null);
function scrollToSection(key: string) {
    const root = scrollEl.value;
    if (!root) return;
    const anchor =
        root.querySelector<HTMLElement>(`[data-group="${key}"]`) ||
        root.querySelector<HTMLElement>(`[data-section="${key}"]`);
    if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function openCmkRoles() {
    openUrl(cmkRolesUrl.value, '_blank');
}

const typeMenuEl = ref<HTMLDetailsElement | null>(null);

function closeTypeMenu() {
    if (typeMenuEl.value) typeMenuEl.value.open = false;
}

function quickClone() {
    closeTypeMenu();
    emit('clone', props.board.name);
    emit('close');
}

async function quickExport() {
    closeTypeMenu();
    try {
        await boardsApi.exportBoard(props.board.name, auth.accessToken!);
    } catch (e: unknown) {
        saveError.value = e instanceof Error ? e.message : 'An error occurred';
    }
}

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

const { names: radarGroupNames } = useRadarGroups(form, () => auth.accessToken);

const radarGroupOptions = computed(() => ({
    type: 'filtered' as const,
    suggestions: radarGroupNames.value.map((name) => ({ name, title: name })),
}));

const saveAttempted = ref(false);
const formBackendValidation = ref<ValidationMessage[]>([]);

const customMissingFields = computed<string[]>(() => {
    const missing: string[] = [];
    if (
        form.value.map_type === 'radar' &&
        (form.value.radar_filter === 'hostgroup' || form.value.radar_filter === 'servicegroup') &&
        !form.value.radar_filter_value
    ) {
        missing.push(t('board.groupName'));
    }
    if (
        form.value.map_type === 'worldmap' &&
        (form.value.worldmap_auto_source === 'hostgroup' ||
            form.value.worldmap_auto_source === 'servicegroup') &&
        !form.value.worldmap_auto_filter_value
    ) {
        missing.push(t('board.groupName'));
    }
    return missing;
});
const customSectionValid = computed(() => customMissingFields.value.length === 0);

const errorMessages = computed<string[]>(() => {
    const out: string[] = [];
    if (saveAttempted.value) {
        for (const f of customMissingFields.value) {
            out.push(t('boardSettings.fieldRequired', { field: f }));
        }
    }
    if (saveError.value) out.push(saveError.value);
    return out;
});

async function save() {
    saveAttempted.value = true;
    if (!customSectionValid.value) {
        return;
    }
    saving.value = true;
    saveError.value = '';
    formBackendValidation.value = [];
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
            const fvd = flowViewFormSpecData.value;
            const rootRaw = (fvd.root as string | undefined)?.trim();
            view = {
                type: 'flow',
                root: rootRaw ? rootRaw : null,
                child_layers: (fvd.child_layers as number | null | undefined) ?? null,
                parent_layers: (fvd.parent_layers as number | null | undefined) ?? null,
                top_affected_hosts: (fvd.top_affected_hosts as number | null | undefined) ?? null,
                max_services_per_host:
                    (fvd.max_services_per_host as number | null | undefined) ?? null,
            };
        } else {
            view = { type: form.value.map_type };
        }
        const fs = formSpecData.value as Record<string, unknown>;
        const rotRaw = fs.rotation_interval;
        let rotationInt = 0;
        if (Array.isArray(rotRaw) && rotRaw.length === 2) {
            const [choice, value] = rotRaw;
            if (choice === 'every' && typeof value === 'number') rotationInt = value;
        }
        await boardsApi.update(
            props.board.name,
            {
                alias: (fs.alias as string) ?? props.board.alias,
                connection_id: (fs.connection_id as string) ?? props.board.connection_id,
                icon_size: (fs.icon_size as number | null | undefined) ?? null,
                rotation_interval: rotationInt,
                click_action: (fs.click_action as boolean | undefined) === false ? 'none' : 'link',
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
        toast.success(t('board.savedToast'));
        emit('updated');
        emit('close');
    } catch (e: unknown) {
        if (e instanceof ApiError && e.status === 409) {
            saveError.value = t('board.staleConflict');
        } else if (e instanceof ApiError && e.status === 422) {
            const detail = (e.detail as { detail?: unknown } | null)?.detail;
            const parsed = toFormValidation(detail, new Set(Object.keys(formSpecData.value)));
            if (parsed) {
                formBackendValidation.value = parsed.messages;
                saveError.value = parsed.stray.map((m) => m.message).join(' ');
            } else {
                saveError.value = e.message;
            }
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
// changed and confirm before discarding edits on cancel/close. Re-taken
// after FormEdit settles in onMounted because the visitor may normalise
// formSpecData on first render (e.g. fill optional fields with defaults),
// which would otherwise look like a user edit.
const initialSnapshot = ref(
    JSON.stringify({
        form: form.value,
        formSpec: formSpecData.value,
        flowView: flowViewFormSpecData.value,
    }),
);
// Tracks bg-image replace-uploads where the resulting filename is identical
// (backend stores under `<board>.<ext>`), so the snapshot comparison can't
// pick them up on its own.
const bgReplaced = ref(false);
const isDirty = computed(
    () =>
        JSON.stringify({
            form: form.value,
            formSpec: formSpecData.value,
            flowView: flowViewFormSpecData.value,
        }) !== initialSnapshot.value ||
        permDraft.size > 0 ||
        bgReplaced.value,
);

const saveButtonTitle = computed(() => {
    if (saving.value) return '';
    if (!isDirty.value) return t('board.saveDisabledClean');
    if (saveAttempted.value && !customSectionValid.value) return t('board.saveDisabledInvalid');
    return '';
});

function requestClose() {
    if (isDirty.value && !window.confirm(t('board.discardChangesConfirm'))) return;
    emit('close');
}

function resetChanges() {
    const snapshot = JSON.parse(initialSnapshot.value) as {
        form: typeof form.value;
        formSpec: Record<string, unknown>;
        flowView: Record<string, unknown>;
    };
    form.value = snapshot.form;
    formSpecData.value = snapshot.formSpec;
    flowViewFormSpecData.value = snapshot.flowView;
    permDraft.clear();
    bgReplaced.value = false;
    saveAttempted.value = false;
    formBackendValidation.value = [];
    saveError.value = '';
}

// Show ⌘ on macOS, Ctrl on the rest; the binding itself uses metaKey on
// macOS and ctrlKey on every other platform.
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '');
const saveShortcutHint = isMac ? '⌘S' : 'Ctrl+S';

function handleKeydown(e: KeyboardEvent) {
    const modifier = isMac ? e.metaKey : e.ctrlKey;
    if (!modifier) return;
    if (e.key === 's' || e.key === 'S' || e.key === 'Enter') {
        e.preventDefault();
        if (!saving.value && isDirty.value && customSectionValid.value) save();
    }
}

async function deleteBoard() {
    const label = props.board.alias || props.board.name;
    if (!window.confirm(t('board.deleteBoardConfirm', { name: label }))) return;
    try {
        await boardsApi.delete(props.board.name, auth.accessToken!);
        toast.success(t('board.deletedToast', { name: label }));
        emit('updated');
        emit('close');
    } catch (e: unknown) {
        saveError.value = e instanceof Error ? e.message : 'An error occurred';
    }
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
    const flowSchemaPromise =
        form.value.map_type === 'flow'
            ? boardsApiFormSpec.getFlowViewSchema(auth.accessToken!).catch((): null => null)
            : Promise.resolve(null);
    const [bs, spec, flowSpec] = await Promise.all([
        connectionsApi.list(auth.accessToken!),
        boardsApiFormSpec.getMetadataSchema(auth.accessToken!).catch((): null => null),
        flowSchemaPromise,
        loadPermissions(),
    ]);
    connections.value = bs;
    schemaLoading.value = false;
    if (spec) formSchema.value = spec as unknown as Schema;
    if (flowSpec) flowViewFormSchema.value = flowSpec as unknown as Schema;
    // Wait for FormEdit's first render to normalise formSpecData, then
    // snapshot again so isDirty doesn't fire on the visitor's own defaults.
    await nextTick();
    initialSnapshot.value = JSON.stringify({
        form: form.value,
        formSpec: formSpecData.value,
        flowView: flowViewFormSpecData.value,
    });
    window.addEventListener('keydown', handleKeydown);
});

onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeydown);
});
</script>

<style scoped>
@reference "tailwindcss";

/* Matches the FormDictionary group-title style (bold, normal case) so the
   custom type-specific sections (Background, Topology, Map view, Filter)
   read as siblings of the FormSpec-rendered "Identification", "Behavior",
   etc. — instead of looking like a separate kind of heading. */
.section-title {
    font-weight: bold;
    font-size: var(--font-size-large);
    color: var(--text);
    margin: 0 0 var(--dimension-3);
}

.orb-input-invalid :deep(input) {
    border-color: var(--form-element-required-color);
}

.board-settings__body {
    display: flex;
    flex-direction: column;
    padding-bottom: var(--dimension-4);
}

/* Compact chip row that combines the read-only board ID and type at the top
   of the settings — replaces two full label/value blocks so the editable
   form starts closer to the slide-in header. */
.board-settings__id-row {
    display: flex;
    align-items: center;
    gap: var(--dimension-3);
    flex-wrap: wrap;
}

.board-settings__id-chip {
    font-family: var(--font-family-mono, monospace);
    font-size: 0.8125rem;
    color: var(--text);
    padding: 4px var(--dimension-3);
    background: var(--bg-elevated, var(--bg-hover));
    border-radius: 999px;
    border: 1px solid var(--border);
}

.board-settings__type-chip {
    font-size: 0.8125rem;
    color: var(--text-muted);
    padding: 4px var(--dimension-3);
    border-radius: 999px;
    border: 1px dashed var(--border);
    cursor: pointer;
    list-style: none;
    display: inline-flex;
    align-items: center;
    gap: var(--dimension-2);
}

.board-settings__type-chip::-webkit-details-marker {
    display: none;
}

.board-settings__type-chip-menu {
    position: relative;
}

.board-settings__type-chip-actions {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: var(--dimension-2);
    z-index: 2;
    display: flex;
    flex-direction: column;
    min-width: 180px;
    padding: var(--dimension-2);
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--dimension-3);
    box-shadow: 0 4px 12px rgb(0 0 0 / 30%);
}

.board-settings__type-chip-action {
    text-align: left;
    padding: var(--dimension-2) var(--dimension-3);
    background: transparent;
    border: 0;
    color: var(--text);
    font-size: 0.875rem;
    cursor: pointer;
    border-radius: var(--dimension-2);
}

.board-settings__type-chip-action:hover {
    background: var(--bg-hover);
}

/* Section jump-nav. Sticky so the operator can navigate sections without
   losing the anchor while scrolling a long form. */
.board-settings__section-nav {
    position: sticky;
    top: 0;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    gap: var(--dimension-2);
    padding: var(--dimension-2) 0;
    background: var(--bg-surface);
}

.board-settings__footer-meta {
    flex: 1;
    display: flex;
    align-items: baseline;
    gap: var(--dimension-3);
    color: var(--text-muted);
    font-size: 0.75rem;
}

.board-settings__footer-shortcut {
    font-family: var(--font-family-mono, monospace);
}

.board-settings__danger-zone {
    margin-top: var(--dimension-6);
    padding: var(--dimension-3) var(--dimension-4);
    border: 1px solid var(--color-light-red-40);
    border-radius: var(--dimension-3);
    background: rgb(var(--color-light-red-40-rgb, 200 30 30) / 5%);
}

.board-settings__danger-zone-summary {
    cursor: pointer;
    font-weight: 600;
    color: var(--color-light-red-40);
}

.board-settings__danger-zone-body {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-3);
    margin-top: var(--dimension-3);
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

/* Hairline divider between each top-level section (Background/Topology/etc.
   and every FormSpec group) — mirrors the GlobalSettings layout so the
   slide-in shares the same visual rhythm. The first section sits flush
   under the chip row, so we only add the divider from the second onward.
   Vue's :deep() doesn't accept comma lists, hence the duplicated rule. */
.board-settings__scroll
    > div
    > .board-settings__type-section
    + :deep(.form-dictionary)
    tr[data-group]
    > td,
.board-settings__scroll :deep(.form-dictionary) tr[data-group] + tr[data-group] > td {
    border-top: 1px solid var(--border);
    padding-top: var(--dimension-5);
    padding-bottom: var(--dimension-5);
}

.board-settings__scroll :deep(.form-dictionary) > tbody > tr[data-group]:first-child > td {
    padding-top: var(--dimension-5);
    padding-bottom: var(--dimension-5);
}

.board-settings__type-section ~ :deep(.form-dictionary) {
    margin-top: 0;
}

.board-settings__type-section {
    padding-bottom: var(--dimension-5);
    border-bottom: 1px solid var(--border);
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
