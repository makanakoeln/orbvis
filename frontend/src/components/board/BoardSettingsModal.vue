<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl w-[34rem] max-h-[85vh] flex flex-col"
            >
                <!-- Header -->
                <div
                    class="flex items-start justify-between shrink-0 border-b border-[var(--border)]"
                    style="padding: 12px 16px"
                >
                    <div>
                        <h3 class="text-base font-bold text-[var(--text)]">
                            {{ t('board.settingsTitle') }}
                        </h3>
                        <p class="text-sm text-zinc-500 font-mono mt-[2px]">{{ board.name }}</p>
                    </div>
                    <button
                        class="p-[5px] rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
                        @click="$emit('close')"
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
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>

                <!-- Tabs -->
                <div class="flex shrink-0" style="gap: 3px; padding: 8px 16px 0">
                    <button
                        v-for="tab in tabs"
                        :key="tab.id"
                        class="rounded-md text-sm font-medium transition-all"
                        style="padding: 3px 8px"
                        :class="
                            activeTab === tab.id
                                ? 'bg-[var(--color-corporate-green-50)]/20 text-[var(--color-corporate-green-40)]'
                                : 'text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)]'
                        "
                        @click="activeTab = tab.id"
                    >
                        {{ tab.label }}
                    </button>
                </div>

                <!-- Tab content -->
                <CmkScrollContainer class="flex-1 min-h-0" style="padding: 10px 16px">
                    <!-- General -->
                    <div v-if="activeTab === 'general'" class="space-y-[10px]">
                        <!-- Alias -->
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.displayName') }}</CmkLabel>
                            <CmkInput v-model="form.alias" field-size="FILL" />
                        </div>

                        <!-- Connection + Icon size -->
                        <div class="grid grid-cols-[1fr_7rem] gap-[8px]">
                            <div class="space-y-[4px]">
                                <CmkLabel>{{ t('board.connection') }}</CmkLabel>
                                <CmkDropdown
                                    :selected-option="form.connection_id || null"
                                    :options="connectionOptions"
                                    :width="'fill'"
                                    :label="t('board.connection')"
                                    @update:selected-option="form.connection_id = $event ?? ''"
                                />
                            </div>
                            <div class="space-y-[4px]">
                                <CmkLabel>{{ t('board.iconSize') }}</CmkLabel>
                                <div class="flex items-center gap-[5px]">
                                    <NumberInput
                                        v-model="form.icon_size"
                                        min="12"
                                        max="96"
                                        class="w-full"
                                    />
                                    <span class="text-sm text-zinc-500 shrink-0">px</span>
                                </div>
                            </div>
                        </div>

                        <!-- Rotation interval -->
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.rotationInterval') }}</CmkLabel>
                            <div class="flex items-center gap-[6px]">
                                <NumberInput
                                    v-model="form.rotation_interval"
                                    min="0"
                                    max="3600"
                                    class="w-[100px]"
                                />
                                <span class="text-sm text-zinc-500 shrink-0">{{
                                    t('board.rotationSuffix')
                                }}</span>
                            </div>
                            <p class="text-sm text-zinc-600">
                                {{ t('board.rotationIntervalHint') }}
                            </p>
                        </div>

                        <!-- Board type -->
                        <div class="space-y-[4px]">
                            <CmkLabel>{{ t('board.boardType') }}</CmkLabel>
                            <CmkDropdown
                                :selected-option="form.map_type || null"
                                :options="mapTypeOptions"
                                :width="'fill'"
                                :label="t('board.boardType')"
                                @update:selected-option="
                                    form.map_type = ($event ?? '') as typeof form.map_type
                                "
                            />
                        </div>

                        <!-- Worldmap settings -->
                        <template v-if="form.map_type === 'worldmap'">
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
                                    <CmkLabel>{{ t('board.zoom') }}</CmkLabel>
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
                            <p class="text-sm text-zinc-600">{{ t('board.worldmapHint') }}</p>

                            <!-- Automap: dynamically populate the board from
                                 host geo-coords (orbvis_lat/orbvis_lng labels
                                 or LAT/LONG custom variables). Mirrors NagVis
                                 automap with lat/lng. -->
                            <div
                                class="space-y-[4px] border-t border-[var(--border)]"
                                style="padding-top: 8px"
                            >
                                <CmkLabel>{{ t('board.autoSource') }}</CmkLabel>
                                <select
                                    v-model="form.worldmap_auto_source"
                                    class="w-full px-[10px] py-[5px] bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)]"
                                >
                                    <option value="">{{ t('board.autoSourceNone') }}</option>
                                    <option value="all_hosts">
                                        {{ t('board.autoSourceAllHosts') }}
                                    </option>
                                    <option value="hostgroup">
                                        {{ t('board.autoSourceHostgroup') }}
                                    </option>
                                    <option value="servicegroup">
                                        {{ t('board.autoSourceServicegroup') }}
                                    </option>
                                </select>
                                <CmkInput
                                    v-if="
                                        form.worldmap_auto_source === 'hostgroup' ||
                                        form.worldmap_auto_source === 'servicegroup'
                                    "
                                    v-model="form.worldmap_auto_filter_value"
                                    :placeholder="t('board.autoFilterValuePlaceholder')"
                                    field-size="FILL"
                                />
                                <p class="text-sm text-zinc-600">
                                    {{ t('board.autoSourceHint') }}
                                </p>
                            </div>
                        </template>

                        <!-- Flow settings -->
                        <template v-if="form.map_type === 'flow'">
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
                                    <CmkLabel>{{ t('board.flowChildLayers') }}</CmkLabel>
                                    <NumberInput
                                        v-model="form.flow_child_layers"
                                        :min="-1"
                                        :max="20"
                                        :placeholder="t('board.flowLayersPlaceholder')"
                                        class="w-full"
                                    />
                                </div>
                                <div class="space-y-[4px]">
                                    <CmkLabel>{{ t('board.flowParentLayers') }}</CmkLabel>
                                    <NumberInput
                                        v-model="form.flow_parent_layers"
                                        :min="-1"
                                        :max="20"
                                        :placeholder="t('board.flowLayersPlaceholder')"
                                        class="w-full"
                                    />
                                </div>
                            </div>
                            <p class="text-sm text-zinc-600">{{ t('board.flowHint') }}</p>

                            <div class="grid grid-cols-2 gap-[8px]">
                                <div class="space-y-[4px]">
                                    <CmkLabel>{{ t('board.flowTopAffectedHosts') }}</CmkLabel>
                                    <NumberInput
                                        v-model="form.flow_top_affected_hosts"
                                        :min="0"
                                        :max="1000"
                                        :placeholder="String(FLOW_TOP_AFFECTED_HOSTS_DEFAULT)"
                                        class="w-full"
                                    />
                                </div>
                                <div class="space-y-[4px]">
                                    <CmkLabel>{{ t('board.flowMaxServicesPerHost') }}</CmkLabel>
                                    <NumberInput
                                        v-model="form.flow_max_services_per_host"
                                        :min="0"
                                        :max="500"
                                        :placeholder="String(FLOW_MAX_SERVICES_PER_HOST_DEFAULT)"
                                        class="w-full"
                                    />
                                </div>
                            </div>
                            <p class="text-sm text-zinc-600">
                                {{ t('board.flowLimitsHint') }}
                            </p>
                        </template>

                        <!-- Radar settings -->
                        <template v-if="form.map_type === 'radar'">
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

                        <!-- Templates -->
                        <div
                            class="space-y-[4px] border-t border-[var(--border)]"
                            style="padding-top: 8px"
                        >
                            <label class="text-sm font-medium text-zinc-400 block mt-[6px]">{{
                                t('boardSettings.templates')
                            }}</label>
                            <label class="text-sm text-zinc-400 block mt-[8px]">{{
                                t('board.hoverTemplate')
                            }}</label>
                            <CmkInput
                                v-model="form.hover_template"
                                :placeholder="t('board.templatePlaceholder')"
                                field-size="FILL"
                            />
                            <label class="text-sm text-zinc-400 block mt-[6px]">{{
                                t('board.contextTemplate')
                            }}</label>
                            <CmkInput
                                v-model="form.context_template"
                                :placeholder="t('board.templatePlaceholder')"
                                field-size="FILL"
                            />
                            <p class="text-sm text-zinc-600">{{ t('board.templateHint') }}</p>
                        </div>

                        <!-- Click action -->
                        <div class="border-t border-[var(--border)]" style="padding-top: 8px">
                            <label class="text-sm font-medium text-zinc-400 block mb-[6px]">{{
                                t('board.clickAction')
                            }}</label>
                            <CmkDropdown
                                :selected-option="form.click_action"
                                :options="clickActionOptions"
                                label=""
                                @update:selected-option="
                                    form.click_action = ($event ?? 'link') as 'link' | 'none'
                                "
                            />
                        </div>

                        <!-- Show in lists toggle -->
                        <div
                            class="flex items-center justify-between border-t border-[var(--border)]"
                            style="padding: 8px 0 4px"
                        >
                            <div>
                                <div class="text-sm font-medium text-[var(--text)]">
                                    {{ t('board.showInLists') }}
                                </div>
                                <div class="text-sm text-zinc-500 mt-[2px]">
                                    {{ t('board.showInListsHint') }}
                                </div>
                            </div>
                            <CmkSwitch v-model:data="form.show_in_lists" />
                        </div>

                        <!-- Background image (static only) -->
                        <div
                            v-if="form.map_type === 'static'"
                            class="space-y-[4px] border-t border-[var(--border)]"
                            style="padding-top: 8px"
                        >
                            <label class="text-sm font-medium text-zinc-400 block mt-[6px]">{{
                                t('board.backgroundImage')
                            }}</label>
                            <div class="flex gap-[6px] mt-[4px]">
                                <CmkInput
                                    v-model="form.background_image"
                                    placeholder="filename.png"
                                    field-size="FILL"
                                />
                                <label
                                    class="flex items-center bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] hover:ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-zinc-400 hover:text-zinc-200 cursor-pointer transition-all shrink-0"
                                    style="padding: 5px 10px"
                                >
                                    {{ t('common.upload') }}
                                    <input
                                        type="file"
                                        accept="image/*"
                                        class="hidden"
                                        @change="uploadBackground"
                                    />
                                </label>
                                <button
                                    v-if="form.background_image"
                                    type="button"
                                    class="bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] hover:ring-red-500 rounded-lg text-sm text-zinc-500 hover:text-red-400 transition-all shrink-0"
                                    style="padding: 5px 10px"
                                    :title="t('board.deleteBackground')"
                                    @click="deleteBackground"
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
                            <p v-if="uploadError" class="text-red-400 text-sm">{{ uploadError }}</p>
                            <p v-if="uploadOk" class="text-green-400 text-xs">
                                {{ t('board.uploadedSuccessfully') }}
                            </p>

                            <label
                                class="text-sm font-medium text-zinc-400 block mt-[10px]"
                                style="margin-top: 12px"
                                >{{ t('board.backgroundColor') }}</label
                            >
                            <ColorInput
                                v-model="form.background_color"
                                :none-label="t('common.none')"
                                default-color="#1f2937"
                            />
                        </div>

                        <p v-if="saveError" class="text-xs text-red-400">{{ saveError }}</p>
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
                                            class="text-left text-sm font-semibold text-zinc-500 tracking-wider"
                                            style="padding: 4px 8px"
                                        >
                                            {{ t('admin.role') }}
                                        </th>
                                        <th
                                            class="text-center text-sm font-semibold text-zinc-500 tracking-wider w-20"
                                            style="padding: 4px 8px"
                                        >
                                            {{ t('common.view') }}
                                        </th>
                                        <th
                                            class="text-center text-sm font-semibold text-zinc-500 tracking-wider w-20"
                                            style="padding: 4px 8px"
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
                                            style="padding: 4px 8px"
                                        >
                                            {{ role.name }}
                                        </td>
                                        <td class="text-center" style="padding: 4px 8px">
                                            <div class="flex items-center justify-center gap-[3px]">
                                                <input
                                                    type="checkbox"
                                                    :checked="hasDraftPerm(role, 'view')"
                                                    :disabled="hasWildcard(role, 'view')"
                                                    class="accent-[var(--color-corporate-green-50)] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                                    style="width: 14px; height: 14px"
                                                    @change="toggleDraftPerm(role, 'view')"
                                                />
                                                <span
                                                    v-if="hasWildcard(role, 'view')"
                                                    class="text-[10px] text-zinc-600"
                                                    :title="t('admin.viaWildcardRule')"
                                                    >*</span
                                                >
                                            </div>
                                        </td>
                                        <td class="text-center" style="padding: 4px 8px">
                                            <div class="flex items-center justify-center gap-[3px]">
                                                <input
                                                    type="checkbox"
                                                    :checked="hasDraftPerm(role, 'edit')"
                                                    :disabled="hasWildcard(role, 'edit')"
                                                    class="accent-[var(--color-corporate-green-50)] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                                    style="width: 14px; height: 14px"
                                                    @change="toggleDraftPerm(role, 'edit')"
                                                />
                                                <span
                                                    v-if="hasWildcard(role, 'edit')"
                                                    class="text-[10px] text-zinc-600"
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
                                class="text-center py-6 text-zinc-600 text-sm"
                            >
                                {{ t('admin.noRoles') }}
                            </p>
                            <p class="text-sm text-zinc-600 mt-3 px-1">
                                * {{ t('admin.wildcardNote') }}
                            </p>
                        </div>
                    </div>
                </CmkScrollContainer>

                <!-- Footer -->
                <div
                    class="flex items-center justify-end shrink-0 border-t border-[var(--border)]"
                    style="gap: 8px; padding: 10px 16px"
                >
                    <CmkButton variant="secondary" @click="$emit('close')">{{
                        t('common.cancel')
                    }}</CmkButton>
                    <CmkButton variant="primary" :disabled="saving" @click="save">
                        {{ saving ? t('common.saving') : t('common.save') }}
                    </CmkButton>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkScrollContainer from '@cmk/components/CmkScrollContainer.vue';
import CmkSwitch from '@cmk/components/CmkSwitch.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError, boardsApi, connectionsApi, rolesApi } from '@/api/client';
import ColorInput from '@/components/ColorInput.vue';
import NumberInput from '@/components/NumberInput.vue';
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
import { boardTypeOptions, lineStyleOptions } from '@/utils/dropdownOptions';

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

const connectionOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: connections.value.map((b) => ({ name: b.id, title: b.label || b.id })),
}));
const mapTypeOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: boardTypeOptions(t),
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
const clickActionOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: 'link', title: t('board.clickActionLink') },
        { name: 'none', title: t('board.clickActionNone') },
    ],
}));
const saveError = ref('');
const uploadError = ref('');
const uploadOk = ref(false);

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
        await boardsApi.update(
            props.board.name,
            {
                alias: form.value.alias,
                connection_id: form.value.connection_id,
                icon_size: form.value.icon_size,
                rotation_interval: form.value.rotation_interval,
                click_action: form.value.click_action,
                show_in_lists: form.value.show_in_lists,
                background_image: form.value.background_image || null,
                background_color: form.value.background_color || null,
                view,
                hover_template: form.value.hover_template || null,
                context_template: form.value.context_template || null,
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

async function uploadBackground(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    uploadError.value = '';
    uploadOk.value = false;
    try {
        const result = await boardsApi.uploadBackground(props.board.name, file, auth.accessToken!);
        form.value.background_image = result.filename;
        uploadOk.value = true;
    } catch (e: unknown) {
        uploadError.value = e instanceof Error ? e.message : 'Upload failed';
    }
}

async function deleteBackground() {
    uploadError.value = '';
    try {
        await boardsApi.deleteBackground(props.board.name, auth.accessToken!);
        form.value.background_image = '';
    } catch (e: unknown) {
        uploadError.value = e instanceof Error ? e.message : 'Delete failed';
    }
}

// ── Permissions ────────────────────────────────────────────────────────────
const permRoles = ref<RoleRead[]>([]);
const permLoading = ref(false);
// Draft: key = `${role_id}-${act}`, value = desired checked state (undefined = use server state)
const permDraft = reactive(new Map<string, boolean>());

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
    const [bs] = await Promise.all([connectionsApi.list(auth.accessToken!), loadPermissions()]);
    connections.value = bs;
});
</script>
