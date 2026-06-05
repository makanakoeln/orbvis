<template>
  <CmkSlideInDialog
    :open="!isPickingView"
    :header="{ title: boardTitle, closeButton: true }"
    :size="showPreview ? 'medium' : 'small'"
    @close="onSlideInClose"
  >
    <div class="board-settings__shell">
      <div class="board-settings__layout">
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
            <div v-if="activeTab === 'general'" class="board-settings__form">
              <!-- Alias -->
              <div class="board-settings__field">
                <CmkLabel>{{ t('board.displayName') }}</CmkLabel>
                <CmkInput v-model="form.alias" field-size="FILL" />
              </div>

              <!-- Connection -->
              <div class="board-settings__field">
                <CmkLabel>{{ t('board.connection') }}</CmkLabel>
                <CmkDropdown
                  :selected-option="form.connection_id || null"
                  :options="connectionOptions"
                  :width="'fill'"
                  :label="t('board.connection')"
                  @update:selected-option="form.connection_id = $event ?? ''"
                />
              </div>

              <!-- Board type (read-only — switching type would invalidate type-specific
                         settings and the board geometry; cloning is the supported path).
                         Rendered as plain text (not Badge) so it doesn't suggest interaction. -->
              <div class="board-settings__field">
                <CmkLabel :help="t('board.boardTypeImmutable')">{{
                  t('board.boardType')
                }}</CmkLabel>
                <p class="board-settings__readonly-value">{{ boardTypeLabel }}</p>
              </div>

              <!-- Rotation (positive toggle replaces the 0=disabled magic value) -->
              <div class="board-settings__field">
                <div class="board-settings__row-between">
                  <CmkLabel :help="t('board.autoRotateHint')">{{ t('board.autoRotate') }}</CmkLabel>
                  <CmkSwitch :data="rotationEnabled" @update:data="onToggleRotation" />
                </div>
                <div v-if="rotationEnabled" class="board-settings__detail">
                  <NumberInput
                    v-model="form.rotation_interval"
                    min="1"
                    max="3600"
                    class="board-settings__num"
                  />
                  <span class="board-settings__unit">{{ t('board.rotationSuffix') }}</span>
                </div>
              </div>

              <!-- Object defaults (per-board overrides of global icon defaults).
                                 The foldertree has no coordinate-positioned icons, so icon
                                 size / layer don't apply. -->
              <div v-if="form.map_type !== 'foldertree'" class="board-settings__subsection">
                <p class="orb-section-title">{{ t('board.objectDefaults') }}</p>
                <div class="board-settings__field">
                  <CmkLabel>{{ t('board.iconSize') }}</CmkLabel>
                  <div class="board-settings__input-row">
                    <NumberInput
                      v-model="form.icon_size"
                      min="12"
                      max="96"
                      :placeholder="String(settingsStore.settings.icon_size)"
                      class="board-settings__num"
                    />
                    <span class="board-settings__unit">px</span>
                  </div>
                </div>
                <div class="board-settings__field">
                  <CmkLabel :help="t('board.defaultZHint')">{{ t('board.defaultZ') }}</CmkLabel>
                  <NumberInput
                    v-model="form.default_z"
                    min="0"
                    max="999"
                    class="board-settings__num"
                  />
                </div>
              </div>

              <!-- Worldmap settings -->
              <template v-if="form.map_type === 'worldmap'">
                <div class="board-settings__coord-row">
                  <div class="board-settings__coord-grid">
                    <div class="board-settings__field">
                      <CmkLabel>{{ t('board.latitude') }}</CmkLabel>
                      <NumberInput
                        v-model="form.worldmap_lat"
                        step="any"
                        :precision="10"
                        class="board-settings__num board-settings__num--full"
                      />
                    </div>
                    <div class="board-settings__field">
                      <CmkLabel>{{ t('board.longitude') }}</CmkLabel>
                      <NumberInput
                        v-model="form.worldmap_lng"
                        step="any"
                        :precision="10"
                        class="board-settings__num board-settings__num--full"
                      />
                    </div>
                    <div class="board-settings__field">
                      <CmkLabel :help="t('board.worldmapHint')">{{ t('board.zoom') }}</CmkLabel>
                      <NumberInput
                        v-model="form.worldmap_zoom"
                        min="1"
                        max="18"
                        class="board-settings__num board-settings__num--full"
                      />
                    </div>
                  </div>
                  <CmkButton
                    variant="secondary"
                    class="board-settings__pick-btn"
                    :title="t('board.pickFromMapHint')"
                    @click="startWorldmapViewPick"
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      aria-hidden="true"
                    >
                      <circle cx="12" cy="12" r="8" />
                      <line x1="12" y1="2" x2="12" y2="6" />
                      <line x1="12" y1="18" x2="12" y2="22" />
                      <line x1="2" y1="12" x2="6" y2="12" />
                      <line x1="18" y1="12" x2="22" y2="12" />
                      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
                    </svg>
                    <span>{{ t('board.pickFromMap') }}</span>
                  </CmkButton>
                </div>
                <div class="board-settings__field">
                  <CmkLabel>{{ t('board.tileUrl') }}</CmkLabel>
                  <CmkInput
                    v-model="form.worldmap_tile_url"
                    :placeholder="t('board.tileUrlPlaceholder')"
                    field-size="FILL"
                  />
                </div>
                <div class="board-settings__field">
                  <CmkLabel>{{ t('board.tileSaturate') }}</CmkLabel>
                  <NumberInput
                    v-model="form.worldmap_tile_saturate"
                    :min="0"
                    :max="100"
                    :step="5"
                    :placeholder="t('board.tileSaturatePlaceholder')"
                    class="board-settings__num board-settings__num--full"
                  />
                </div>

                <!-- Automap: dynamically populate the board from
                                 host geo-coords (orbvis_lat/orbvis_lng labels
                                 or LAT/LONG custom variables). Mirrors NagVis
                                 automap with lat/lng. -->
                <div class="board-settings__subsection board-settings__field">
                  <CmkLabel :help="t('board.autoSourceHint')">{{ t('board.autoSource') }}</CmkLabel>
                  <CmkDropdown
                    :selected-option="form.worldmap_auto_source || ''"
                    :options="worldmapAutoSourceOptions"
                    :width="'fill'"
                    :label="t('board.autoSource')"
                    @update:selected-option="
                      form.worldmap_auto_source = ($event ?? '') as typeof form.worldmap_auto_source
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
                <div class="board-settings__field">
                  <CmkLabel>{{ t('board.flowRoot') }}</CmkLabel>
                  <CmkInput
                    v-model="form.flow_root"
                    :placeholder="t('board.flowRootPlaceholder')"
                    field-size="FILL"
                  />
                </div>
                <div class="board-settings__grid-2">
                  <div class="board-settings__field">
                    <CmkLabel :help="t('board.flowHint')">{{
                      t('board.flowChildLayers')
                    }}</CmkLabel>
                    <NumberInput
                      v-model="form.flow_child_layers"
                      :min="-1"
                      :max="20"
                      :placeholder="t('board.flowLayersPlaceholder')"
                      class="board-settings__num board-settings__num--full"
                    />
                  </div>
                  <div class="board-settings__field">
                    <CmkLabel :help="t('board.flowHint')">{{
                      t('board.flowParentLayers')
                    }}</CmkLabel>
                    <NumberInput
                      v-model="form.flow_parent_layers"
                      :min="-1"
                      :max="20"
                      :placeholder="t('board.flowLayersPlaceholder')"
                      class="board-settings__num board-settings__num--full"
                    />
                  </div>
                </div>

                <div class="board-settings__grid-2">
                  <div class="board-settings__field">
                    <CmkLabel :help="t('board.flowLimitsHint')">{{
                      t('board.flowTopAffectedHosts')
                    }}</CmkLabel>
                    <NumberInput
                      v-model="form.flow_top_affected_hosts"
                      :min="0"
                      :max="1000"
                      :placeholder="String(FLOW_TOP_AFFECTED_HOSTS_DEFAULT)"
                      class="board-settings__num board-settings__num--full"
                    />
                  </div>
                  <div class="board-settings__field">
                    <CmkLabel :help="t('board.flowLimitsHint')">{{
                      t('board.flowMaxServicesPerHost')
                    }}</CmkLabel>
                    <NumberInput
                      v-model="form.flow_max_services_per_host"
                      :min="0"
                      :max="500"
                      :placeholder="String(FLOW_MAX_SERVICES_PER_HOST_DEFAULT)"
                      class="board-settings__num board-settings__num--full"
                    />
                  </div>
                </div>
              </template>

              <!-- Radar settings -->
              <template v-if="form.map_type === 'radar'">
                <div class="board-settings__grid-2">
                  <div class="board-settings__field">
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
                    v-if="form.radar_filter === 'hostgroup' || form.radar_filter === 'servicegroup'"
                    class="board-settings__field"
                  >
                    <CmkLabel>{{ t('board.groupName') }}</CmkLabel>
                    <AutocompleteInput
                      v-model="form.radar_filter_value"
                      :suggestions="radarGroupNames"
                      :loading="loadingRadarGroups"
                      :placeholder="t('boardSettings.groupName')"
                      :empty-text="
                        t(
                          form.radar_filter === 'hostgroup'
                            ? 'boardSettings.noHostgroups'
                            : 'boardSettings.noServicegroups'
                        )
                      "
                    />
                  </div>
                </div>
              </template>

              <template v-if="form.map_type === 'foldertree'">
                <div class="board-settings__grid-2">
                  <div class="board-settings__field">
                    <CmkLabel :help="t('board.ftRootFolderHint')">{{
                      t('board.ftRootFolder')
                    }}</CmkLabel>
                    <CmkDropdown
                      :selected-option="form.ft_root_folder"
                      :options="ftRootFolderOptions"
                      :width="'fill'"
                      :label="t('board.ftRootFolder')"
                      @update:selected-option="form.ft_root_folder = $event ?? ''"
                    />
                  </div>
                  <div class="board-settings__field">
                    <CmkLabel :help="t('board.ftExpandDepthHint')">{{
                      t('board.ftExpandDepth')
                    }}</CmkLabel>
                    <NumberInput
                      v-model="form.ft_default_expand_depth"
                      min="0"
                      max="20"
                      class="board-settings__num"
                    />
                  </div>
                </div>
                <div class="board-settings__field">
                  <CmkLabel :help="t('board.ftDefaultViewHint')">{{
                    t('board.ftDefaultView')
                  }}</CmkLabel>
                  <CmkDropdown
                    :selected-option="form.ft_default_view"
                    :options="ftDefaultViewOptions"
                    :width="'fill'"
                    :label="t('board.ftDefaultView')"
                    @update:selected-option="
                      form.ft_default_view = ($event as 'list' | 'map') ?? 'list'
                    "
                  />
                </div>
                <div class="board-settings__field">
                  <CmkLabel :help="t('board.ftSitesHint')">{{ t('board.ftSites') }}</CmkLabel>
                  <FtSitesSelect v-model="ftSites" :options="siteOptions" />
                </div>
                <div class="board-settings__toggle-list">
                  <label class="board-settings__toggle">
                    <CmkSwitch v-model:data="form.ft_show_empty_folders" />
                    <span class="board-settings__toggle-label">{{
                      t('board.ftShowEmptyFolders')
                    }}</span>
                  </label>
                  <label class="board-settings__toggle">
                    <CmkSwitch v-model:data="form.ft_show_services" />
                    <span class="board-settings__toggle-label">{{
                      t('board.ftShowServices')
                    }}</span>
                  </label>
                  <label class="board-settings__toggle">
                    <CmkSwitch v-model:data="form.ft_problems_only" />
                    <span class="board-settings__toggle-label">{{
                      t('board.ftProblemsOnly')
                    }}</span>
                  </label>
                  <label class="board-settings__toggle">
                    <CmkSwitch v-model:data="form.ft_only_hard_states" />
                    <span class="board-settings__toggle-label">{{
                      t('board.ftOnlyHardStates')
                    }}</span>
                  </label>
                </div>
              </template>

              <!-- Templates: radar cards and the foldertree tree have no
                                 per-object hover / context popups, so the templates never apply. -->
              <div
                v-if="form.map_type !== 'radar' && form.map_type !== 'foldertree'"
                class="board-settings__subsection board-settings__stack"
              >
                <p class="orb-section-title">{{ t('boardSettings.templates') }}</p>
                <div class="board-settings__field">
                  <CmkLabel :help="t('board.templateHint')">{{
                    t('board.hoverTemplate')
                  }}</CmkLabel>
                  <CmkInput
                    v-model="form.hover_template"
                    :placeholder="t('board.templatePlaceholder')"
                    field-size="FILL"
                  />
                </div>
                <div class="board-settings__field">
                  <CmkLabel :help="t('board.templateHint')">{{
                    t('board.contextTemplate')
                  }}</CmkLabel>
                  <CmkInput
                    v-model="form.context_template"
                    :placeholder="t('board.templatePlaceholder')"
                    field-size="FILL"
                  />
                </div>
              </div>

              <!-- Click action -->
              <div class="board-settings__subsection board-settings__field">
                <div>
                  <CmkLabel>{{ t('board.clickAction') }}</CmkLabel>
                </div>
                <CmkDropdown
                  :selected-option="form.click_action"
                  :options="clickActionOptions"
                  :width="'fill'"
                  label=""
                  @update:selected-option="
                    form.click_action = ($event ?? 'link') as 'link' | 'none'
                  "
                />
              </div>

              <!-- Rendering style (static boards) -->
              <div
                v-if="form.map_type === 'static'"
                class="board-settings__subsection board-settings__field"
              >
                <div>
                  <CmkLabel :help="t('board.renderModeHint')">{{ t('board.renderMode') }}</CmkLabel>
                </div>
                <CmkDropdown
                  :selected-option="form.render_mode"
                  :options="renderModeOptions"
                  :width="'fill'"
                  label=""
                  @update:selected-option="
                    form.render_mode = ($event ?? 'default') as 'default' | 'nagvis_classic'
                  "
                />
              </div>

              <!-- Show in lists toggle -->
              <div class="board-settings__subsection board-settings__row-between">
                <CmkLabel :help="t('board.showInListsHint')">{{ t('board.showInLists') }}</CmkLabel>
                <CmkSwitch v-model:data="form.show_in_lists" />
              </div>

              <!-- Background (static only) -->
              <div
                v-if="form.map_type === 'static'"
                class="board-settings__subsection board-settings__stack"
              >
                <p class="orb-section-title">{{ t('boardSettings.background') }}</p>
                <div class="board-settings__field">
                  <CmkLabel>{{ t('board.backgroundImage') }}</CmkLabel>
                  <BackgroundImageUpload
                    v-model:pending-file="pendingBgFile"
                    v-model:pending-remove="pendingBgRemove"
                    :model-value="form.background_image"
                    :pending-preview-url="pendingBgPreviewUrl"
                  />
                </div>
                <div class="board-settings__field">
                  <CmkLabel>{{ t('board.backgroundColor') }}</CmkLabel>
                  <ColorInput
                    v-model="form.background_color"
                    :enable-label="t('common.useColor')"
                    default-color="#1f2937"
                  />
                </div>
              </div>

              <p v-if="saveError" class="board-settings__error">
                {{ saveError }}
              </p>
            </div>

            <!-- Permissions -->
            <div v-else-if="activeTab === 'permissions'">
              <div v-if="permLoading" class="board-settings__perm-loading">
                <CmkLoading />
              </div>
              <div v-else>
                <table class="board-settings__perm-table">
                  <thead>
                    <tr class="board-settings__perm-head-row">
                      <th class="board-settings__perm-th">
                        {{ t('admin.role') }}
                      </th>
                      <th class="board-settings__perm-th board-settings__perm-th--center">
                        {{ t('common.view') }}
                      </th>
                      <th class="board-settings__perm-th board-settings__perm-th--center">
                        {{ t('common.edit') }}
                      </th>
                    </tr>
                  </thead>
                  <tbody class="board-settings__perm-body">
                    <tr
                      v-for="role in permRoles"
                      :key="role.role_id"
                      class="board-settings__perm-row"
                    >
                      <td class="board-settings__perm-td board-settings__perm-td--name">
                        {{ role.name }}
                      </td>
                      <td class="board-settings__perm-td board-settings__perm-td--center">
                        <div class="board-settings__perm-cell">
                          <CmkCheckbox
                            :model-value="hasDraftPerm(role, 'view')"
                            :disabled="hasWildcard(role, 'view')"
                            @update:model-value="toggleDraftPerm(role, 'view')"
                          />
                          <span
                            v-if="hasWildcard(role, 'view')"
                            class="board-settings__perm-wildcard"
                            :title="t('admin.viaWildcardRule')"
                            >*</span
                          >
                        </div>
                      </td>
                      <td class="board-settings__perm-td board-settings__perm-td--center">
                        <div class="board-settings__perm-cell">
                          <CmkCheckbox
                            :model-value="hasDraftPerm(role, 'edit')"
                            :disabled="hasWildcard(role, 'edit')"
                            @update:model-value="toggleDraftPerm(role, 'edit')"
                          />
                          <span
                            v-if="hasWildcard(role, 'edit')"
                            class="board-settings__perm-wildcard"
                            :title="t('admin.viaWildcardRule')"
                            >*</span
                          >
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p v-if="!permRoles.length" class="board-settings__perm-empty">
                  {{ t('admin.noRoles') }}
                </p>
                <p class="board-settings__perm-note">* {{ t('admin.wildcardNote') }}</p>
              </div>
            </div>
          </div>
        </div>

        <aside v-if="showPreview" class="board-settings__preview">
          <span class="board-settings__preview-label">{{ t('board.previewLabel') }}</span>
          <div class="board-settings__preview-stage">
            <iframe
              ref="previewIframe"
              :src="previewUrl"
              class="board-settings__preview-frame"
              :title="t('board.previewLabel')"
              @load="onPreviewLoaded"
            />
          </div>
        </aside>
      </div>

      <div class="board-settings__footer">
        <button type="button" class="board-settings__preview-toggle" @click="togglePreview">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <template v-if="showPreview">
              <path
                d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"
              />
              <path
                d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.46 18.46 0 0 1-2.16 3.19"
              />
              <line x1="1" y1="1" x2="23" y2="23" />
            </template>
            <template v-else>
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </template>
          </svg>
          <span>{{ showPreview ? t('board.hidePreview') : t('board.showPreview') }}</span>
        </button>
        <span class="board-settings__footer-spacer" />
        <CmkButton variant="secondary" @click="$emit('close')">
          {{ t('common.cancel') }}
        </CmkButton>
        <CmkButton variant="primary" :disabled="saving" @click="save">
          {{ saving ? t('common.saving') : t('common.save') }}
        </CmkButton>
      </div>
    </div>
  </CmkSlideInDialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import ColorInput from '@/components/ColorInput.vue'
import NumberInput from '@/components/NumberInput.vue'
import CmkButton from '@/components/cmk/CmkButton'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkLabel from '@/components/cmk/CmkLabel'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkSlideInDialog from '@/components/cmk/CmkSlideInDialog'
import CmkSwitch from '@/components/cmk/CmkSwitch'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { ApiError, boardsApi, connectionsApi, rolesApi } from '@/api/client'
import { useRadarGroups } from '@/composables/useRadarGroups'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import type {
  BoardRead,
  ConnectionConfig,
  FlowView,
  FolderTreeView,
  PermissionRead,
  RadarView,
  RoleRead,
  WorldmapView
} from '@/types/api'
import { boardTypeOptions } from '@/utils/dropdownOptions'
import { PREVIEW_EDIT, PREVIEW_READY } from '@/utils/previewBridge'

import AutocompleteInput from './AutocompleteInput.vue'
import BackgroundImageUpload from './BackgroundImageUpload.vue'
import FtSitesSelect from './FtSitesSelect.vue'

// Mirror of backend `Settings.flow_board_*` defaults — shown as placeholder so
// the user knows which value applies when the field is left empty.
const FLOW_TOP_AFFECTED_HOSTS_DEFAULT = 25
const FLOW_MAX_SERVICES_PER_HOST_DEFAULT = 50

const props = defineProps<{
  board: BoardRead
  worldmapView?: { lat: number; lng: number; zoom: number } | null
}>()
const emit = defineEmits<{
  close: []
  updated: []
  pickWorldmapView: [done: (view: { lat: number; lng: number; zoom: number } | null) => void]
  worldmapViewChange: [view: { lat: number; lng: number; zoom: number }]
}>()

const PREVIEW_PREF_KEY = 'orbvis.boardSettings.previewVisible'
const showPreview = ref(
  typeof window !== 'undefined' && window.localStorage?.getItem(PREVIEW_PREF_KEY) === '1'
)
function togglePreview() {
  showPreview.value = !showPreview.value
  try {
    window.localStorage?.setItem(PREVIEW_PREF_KEY, showPreview.value ? '1' : '0')
  } catch {
    // Private-Mode oder Storage voll — Toggle wirkt nur in dieser Sitzung.
  }
}

const isPickingView = ref(false)
function startWorldmapViewPick() {
  if (isPickingView.value) return
  isPickingView.value = true
  emit('pickWorldmapView', (view) => {
    isPickingView.value = false
    if (view) {
      form.value.worldmap_lat = view.lat
      form.value.worldmap_lng = view.lng
      form.value.worldmap_zoom = view.zoom
    }
  })
}
function onSlideInClose() {
  if (isPickingView.value) return
  emit('close')
}

const { t } = useI18n()
const auth = useAuthStore()
const settingsStore = useSettingsStore()

const tabs = computed<{ id: 'general' | 'permissions'; label: string }[]>(() => {
  const isCmk = auth.ssoActive || auth.isCheckmkDeployment
  return [
    { id: 'general', label: t('admin.settings') },
    ...(!isCmk ? [{ id: 'permissions' as const, label: t('admin.boardPermissions') }] : [])
  ]
})
const activeTab = ref<'general' | 'permissions'>('general')

const localVersion = ref<number | null>(props.board.version ?? null)
// Background image is staged and only uploaded/removed on save, so closing
// without saving leaves the server untouched (upload → save).
const pendingBgFile = ref<File | null>(null)
const pendingBgRemove = ref(false)

// Mirror the staged background file as a data: URL so the live preview can show
// it before save — the server filename only exists after upload. Must be a
// data: URL (not blob:): Checkmk's CSP allows ``img-src ... data:`` but blocks
// blob:, so a blob: URL would render nothing on OMD sites.
const pendingBgPreviewUrl = ref<string | null>(null)
let bgReadSeq = 0
watch(pendingBgFile, (file) => {
  const seq = ++bgReadSeq
  if (!file) {
    pendingBgPreviewUrl.value = null
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    if (seq === bgReadSeq) pendingBgPreviewUrl.value = reader.result as string
  }
  reader.readAsDataURL(file)
})

// ── General ────────────────────────────────────────────────────────────────

function initWorldmapCoords() {
  if (props.worldmapView) {
    return {
      lat: props.worldmapView.lat,
      lng: props.worldmapView.lng,
      zoom: props.worldmapView.zoom
    }
  }
  if (props.board.view.type === 'worldmap') {
    const wv = props.board.view as WorldmapView
    return { lat: wv.lat, lng: wv.lng, zoom: wv.zoom }
  }
  return { lat: 51.0, lng: 10.0, zoom: 5 }
}

const wm = initWorldmapCoords()
const rv = props.board.view.type === 'radar' ? (props.board.view as RadarView) : null
const wmv = props.board.view.type === 'worldmap' ? (props.board.view as WorldmapView) : null
const fv = props.board.view.type === 'flow' ? (props.board.view as FlowView) : null
const ftv = props.board.view.type === 'foldertree' ? (props.board.view as FolderTreeView) : null

const form = ref({
  alias: props.board.alias,
  connection_id: props.board.connection_id,
  icon_size: props.board.icon_size,
  rotation_interval: props.board.rotation_interval,
  click_action: (props.board.click_action ?? 'link') as 'link' | 'none',
  render_mode: (props.board.render_mode ?? 'default') as 'default' | 'nagvis_classic',
  default_z: props.board.default_z ?? 1,
  show_in_lists: props.board.show_in_lists !== false,
  map_type: props.board.view.type,
  worldmap_auto_source: (wmv?.auto_source ?? '') as '' | 'all_hosts' | 'hostgroup' | 'servicegroup',
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
  ft_root_folder: ftv?.root_folder ?? '',
  ft_default_view: (ftv?.default_view ?? 'list') as 'list' | 'map',
  ft_default_expand_depth: ftv?.default_expand_depth ?? 1,
  ft_show_services: ftv?.show_services ?? false,
  ft_show_empty_folders: ftv?.show_empty_folders ?? true,
  ft_problems_only: ftv?.problems_only ?? false,
  ft_only_hard_states: ftv?.only_hard_states ?? false,
  ft_sites: (ftv?.sites ?? []).join(', '),
  hover_template: props.board.hover_template ?? '',
  context_template: props.board.context_template ?? '',
  background_image: props.board.background_image ?? '',
  background_color: props.board.background_color ?? ''
})

const connections = ref<ConnectionConfig[]>([])
const saving = ref(false)

watch(
  () => [form.value.worldmap_lat, form.value.worldmap_lng, form.value.worldmap_zoom] as const,
  ([lat, lng, zoom]) => {
    if (form.value.map_type === 'worldmap') {
      emit('worldmapViewChange', { lat, lng, zoom })
    }
  }
)

const connectionOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: connections.value.map((b) => ({ name: b.id, title: b.label || b.id }))
}))
const boardTypeLabel = computed(
  () =>
    // Resolve the label for whatever type the board already is, so a folder
    // board still shows its proper name even when the feature flag is off.
    boardTypeOptions(t, true).find((o) => o.name === form.value.map_type)?.title ??
    form.value.map_type
)

const boardTitle = computed(() => t('board.settingsTitle') + ' — ' + props.board.name)

const rotationEnabled = computed(() => (form.value.rotation_interval ?? 0) > 0)

function onToggleRotation(checked: boolean) {
  form.value.rotation_interval = checked ? Math.max(form.value.rotation_interval || 30, 1) : 0
}
const worldmapAutoSourceOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: t('board.autoSourceNone') },
    { name: 'all_hosts', title: t('board.autoSourceAllHosts') },
    { name: 'hostgroup', title: t('board.autoSourceHostgroup') },
    { name: 'servicegroup', title: t('board.autoSourceServicegroup') }
  ]
}))
const radarFilterOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'hostgroup', title: t('board.filterTypeHostgroup') },
    { name: 'servicegroup', title: t('board.filterTypeServicegroup') },
    { name: 'all_hosts', title: t('board.filterTypeAllHosts') },
    { name: 'all_services', title: t('board.filterTypeAllServices') }
  ]
}))
const folderOptions = ref<{ path: string; title: string }[]>([])
const ftDefaultViewOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'list', title: t('board.ftViewList') },
    { name: 'map', title: t('board.ftViewMap') }
  ]
}))
const ftRootFolderOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: t('board.ftRootFolderAll') },
    ...folderOptions.value.map((f) => ({ name: f.path, title: f.title }))
  ]
}))
async function loadFolderOptions() {
  if (form.value.map_type !== 'foldertree' || !form.value.connection_id) return
  try {
    folderOptions.value = await connectionsApi.folders(form.value.connection_id, auth.accessToken!)
  } catch {
    folderOptions.value = []
  }
}

const siteOptions = ref<{ id: string; alias: string }[]>([])
async function loadSiteOptions() {
  if (form.value.map_type !== 'foldertree' || !form.value.connection_id) return
  try {
    siteOptions.value = await connectionsApi.sites(form.value.connection_id, auth.accessToken!)
  } catch {
    siteOptions.value = []
  }
}

// form.ft_sites is the comma-joined wire shape; FtSitesSelect works on an id array.
const ftSites = computed<string[]>({
  get: () =>
    form.value.ft_sites
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  set: (v) => {
    form.value.ft_sites = v.join(', ')
  }
})
const clickActionOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'link', title: t('board.clickActionLink') },
    { name: 'none', title: t('board.clickActionNone') }
  ]
}))
const renderModeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'default', title: t('board.renderModeDefault') },
    { name: 'nagvis_classic', title: t('board.renderModeNagvisClassic') }
  ]
}))
const saveError = ref('')

const { names: radarGroupNames, loading: loadingRadarGroups } = useRadarGroups(
  form,
  () => auth.accessToken
)

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    // Always save any pending permission changes
    if (permDraft.size > 0) {
      await savePermissions()
    }
    // Stage-then-save: the chosen background only hits the server now, so
    // closing without saving never persists it. Both endpoints bump the
    // board version, so adopt it before the If-Match-gated update below.
    if (pendingBgRemove.value) {
      const { version } = await boardsApi.deleteBackground(props.board.name, auth.accessToken!)
      form.value.background_image = ''
      if (version != null) localVersion.value = version
    } else if (pendingBgFile.value) {
      const { filename, version } = await boardsApi.uploadBackground(
        props.board.name,
        pendingBgFile.value,
        auth.accessToken!
      )
      form.value.background_image = filename
      if (version != null) localVersion.value = version
    }
    let view: Record<string, unknown>
    if (form.value.map_type === 'worldmap') {
      view = {
        type: 'worldmap',
        lat: form.value.worldmap_lat,
        lng: form.value.worldmap_lng,
        zoom: form.value.worldmap_zoom,
        auto_source: form.value.worldmap_auto_source || null,
        auto_filter_value: form.value.worldmap_auto_filter_value,
        tile_url: form.value.worldmap_tile_url || null,
        tile_saturate: form.value.worldmap_tile_saturate
      }
    } else if (form.value.map_type === 'radar') {
      view = {
        type: 'radar',
        filter: form.value.radar_filter,
        filter_value: form.value.radar_filter_value
      }
    } else if (form.value.map_type === 'flow') {
      view = {
        type: 'flow',
        root: form.value.flow_root.trim() || null,
        child_layers: form.value.flow_child_layers,
        parent_layers: form.value.flow_parent_layers,
        top_affected_hosts: form.value.flow_top_affected_hosts,
        max_services_per_host: form.value.flow_max_services_per_host
      }
    } else if (form.value.map_type === 'foldertree') {
      view = {
        type: 'foldertree',
        root_folder: form.value.ft_root_folder.trim(),
        default_view: form.value.ft_default_view,
        default_expand_depth: form.value.ft_default_expand_depth,
        show_services: form.value.ft_show_services,
        show_empty_folders: form.value.ft_show_empty_folders,
        problems_only: form.value.ft_problems_only,
        only_hard_states: form.value.ft_only_hard_states,
        sites: form.value.ft_sites
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      }
    } else {
      view = { type: form.value.map_type }
    }
    await boardsApi.update(
      props.board.name,
      {
        alias: form.value.alias,
        connection_id: form.value.connection_id,
        icon_size: form.value.icon_size,
        rotation_interval: form.value.rotation_interval,
        click_action: form.value.click_action,
        render_mode: form.value.render_mode,
        default_z: form.value.default_z,
        show_in_lists: form.value.show_in_lists,
        background_image: form.value.background_image || null,
        background_color: form.value.background_color || null,
        view,
        hover_template: form.value.hover_template || null,
        context_template: form.value.context_template || null
      },
      auth.accessToken!,
      localVersion.value
    )
    emit('updated')
    emit('close')
  } catch (e: unknown) {
    // 409 means another operator saved this board after we opened it.
    // Surface a clear message instead of the generic "An error occurred"
    // so the operator can reload and reconcile.
    if (e instanceof ApiError && e.status === 409) {
      saveError.value = t('board.staleConflict')
    } else {
      saveError.value = e instanceof Error ? e.message : 'An error occurred'
    }
  } finally {
    saving.value = false
  }
}

// ── Live preview ───────────────────────────────────────────────────────────
const previewIframe = ref<HTMLIFrameElement | null>(null)
const previewUrl = computed(
  () => `${window.location.pathname}#/boards/${encodeURIComponent(props.board.name)}?preview=1`
)

function buildPreviewView(): Record<string, unknown> {
  if (form.value.map_type === 'worldmap') {
    return {
      type: 'worldmap',
      lat: form.value.worldmap_lat,
      lng: form.value.worldmap_lng,
      zoom: form.value.worldmap_zoom,
      auto_source: form.value.worldmap_auto_source || null,
      auto_filter_value: form.value.worldmap_auto_filter_value,
      tile_url: form.value.worldmap_tile_url || null,
      tile_saturate: form.value.worldmap_tile_saturate
    }
  }
  if (form.value.map_type === 'radar') {
    return {
      type: 'radar',
      filter: form.value.radar_filter,
      filter_value: form.value.radar_filter_value
    }
  }
  if (form.value.map_type === 'flow') {
    return {
      type: 'flow',
      root: form.value.flow_root.trim() || null,
      child_layers: form.value.flow_child_layers,
      parent_layers: form.value.flow_parent_layers,
      top_affected_hosts: form.value.flow_top_affected_hosts,
      max_services_per_host: form.value.flow_max_services_per_host
    }
  }
  if (form.value.map_type === 'foldertree') {
    return {
      type: 'foldertree',
      root_folder: form.value.ft_root_folder.trim(),
      default_view: form.value.ft_default_view,
      default_expand_depth: form.value.ft_default_expand_depth,
      show_services: form.value.ft_show_services,
      show_empty_folders: form.value.ft_show_empty_folders,
      problems_only: form.value.ft_problems_only,
      only_hard_states: form.value.ft_only_hard_states,
      sites: form.value.ft_sites
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    }
  }
  return { type: form.value.map_type }
}

function postPreviewPatch() {
  const win = previewIframe.value?.contentWindow
  if (!win) return
  const patch = {
    alias: form.value.alias,
    icon_size: form.value.icon_size,
    hover_template: form.value.hover_template || '',
    context_template: form.value.context_template || '',
    background_color: form.value.background_color || null,
    view: buildPreviewView()
  }
  win.postMessage({ source: PREVIEW_EDIT, patch }, window.location.origin)
}

// The background image (a potentially multi-MB data: URL) is posted on its own
// channel, only when it changes — keeping it out of the debounced general patch
// avoids re-cloning megabytes through postMessage on every unrelated edit.
function postBgPatch() {
  const win = previewIframe.value?.contentWindow
  if (!win) return
  const background_image = pendingBgRemove.value
    ? null
    : (pendingBgPreviewUrl.value ?? form.value.background_image) || null
  win.postMessage({ source: PREVIEW_EDIT, patch: { background_image } }, window.location.origin)
}

let previewDebounceTimer: ReturnType<typeof setTimeout> | null = null
function schedulePreviewPost() {
  if (previewDebounceTimer) clearTimeout(previewDebounceTimer)
  previewDebounceTimer = setTimeout(postPreviewPatch, 120)
}

function onPreviewLoaded() {
  postPreviewPatch()
  postBgPatch()
}

function onPreviewReady(ev: MessageEvent) {
  if (ev.origin !== window.location.origin) return
  const data = ev.data as { source?: string } | null
  if (!data || data.source !== PREVIEW_READY) return
  if (ev.source !== previewIframe.value?.contentWindow) return
  postPreviewPatch()
  postBgPatch()
}

watch(form, schedulePreviewPost, { deep: true })
watch([pendingBgPreviewUrl, pendingBgRemove], postBgPatch)

// ── Permissions ────────────────────────────────────────────────────────────
const permRoles = ref<RoleRead[]>([])
const permLoading = ref(false)
// Draft: key = `${role_id}-${act}`, value = desired checked state (undefined = use server state)
const permDraft = reactive(new Map<string, boolean>())

async function loadPermissions() {
  permLoading.value = true
  try {
    permRoles.value = await rolesApi.list(auth.accessToken!)
    permDraft.clear()
  } finally {
    permLoading.value = false
  }
}

function hasWildcard(role: RoleRead, act: string): boolean {
  return role.permissions.some((p) => p.mod === 'map' && p.act === act && p.obj === '*')
}

function hasDirectPerm(role: RoleRead, act: string): boolean {
  return role.permissions.some(
    (p) => p.mod === 'map' && p.act === act && p.obj === props.board.name
  )
}

function hasDraftPerm(role: RoleRead, act: string): boolean {
  const key = `${role.role_id}-${act}`
  if (permDraft.has(key)) return permDraft.get(key)!
  return hasDirectPerm(role, act) || hasWildcard(role, act)
}

function toggleDraftPerm(role: RoleRead, act: string) {
  if (hasWildcard(role, act)) return
  const key = `${role.role_id}-${act}`
  const current = hasDraftPerm(role, act)
  permDraft.set(key, !current)
}

async function savePermissions() {
  for (const role of permRoles.value) {
    for (const act of ['view', 'edit'] as const) {
      if (hasWildcard(role, act)) continue
      const key = `${role.role_id}-${act}`
      if (!permDraft.has(key)) continue // no change
      const desired = permDraft.get(key)!
      const hasServer = hasDirectPerm(role, act)
      if (desired && !hasServer) {
        // add
        let existingPerm: PermissionRead | null = null
        for (const r of permRoles.value) {
          const p = r.permissions.find(
            (p) => p.mod === 'map' && p.act === act && p.obj === props.board.name
          )
          if (p) {
            existingPerm = p
            break
          }
        }
        if (!existingPerm) {
          existingPerm = await rolesApi.createPermission(
            'map',
            act,
            props.board.name,
            auth.accessToken!
          )
        }
        await rolesApi.assignPermission(role.role_id, existingPerm.perm_id, auth.accessToken!)
      } else if (!desired && hasServer) {
        // remove
        const perm = role.permissions.find(
          (p) => p.mod === 'map' && p.act === act && p.obj === props.board.name
        )!
        await rolesApi.removePermission(role.role_id, perm.perm_id, auth.accessToken!)
      }
    }
  }
  permDraft.clear()
}

onMounted(async () => {
  const [bs] = await Promise.all([connectionsApi.list(auth.accessToken!), loadPermissions()])
  connections.value = bs
  void loadFolderOptions()
  void loadSiteOptions()
  window.addEventListener('message', onPreviewReady)
})

watch(
  () => form.value.connection_id,
  () => {
    void loadFolderOptions()
    void loadSiteOptions()
  }
)

onBeforeUnmount(() => {
  window.removeEventListener('message', onPreviewReady)
  if (previewDebounceTimer) clearTimeout(previewDebounceTimer)
})
</script>

<style scoped>
.board-settings__shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.board-settings__layout {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-5);
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.board-settings__body {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--dimension-4);
  flex: 1 1 60%;
  min-width: 0;
}

.board-settings__preview {
  flex: 1 1 40%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  border-left: 1px solid var(--border);
  padding-left: var(--dimension-4);
  position: sticky;
  top: 0;
  align-self: flex-start;
  max-height: calc(100vh - 120px);
}

.board-settings__preview-label {
  font-size: var(--font-size-small, 0.8125rem);
  font-weight: 600;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.board-settings__preview-stage {
  position: relative;
  flex: 1;
  display: flex;
}

.board-settings__preview-frame {
  flex: none;
  width: 100%;
  aspect-ratio: 4 / 3;
  border: 1px solid var(--border);
  border-radius: var(--dimension-3);
  background: var(--bg-elevated, var(--bg-hover));
}

.board-settings__preview-toggle {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-4);
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  cursor: pointer;
  font-size: var(--font-size-normal);
}

.board-settings__preview-toggle:hover {
  background: var(--bg-hover);
}

.board-settings__footer-spacer {
  flex: 1;
}

/* Read-only display for unchangeable values (e.g. board type). Plain text
   on the form background so it doesn't suggest a button or pill. */
.board-settings__readonly-value {
  font-size: var(--font-size-normal);
  color: var(--text);
  margin: 0;
  padding: var(--dimension-1) 0;
}

/* Detail field that appears below a toggle, slightly indented so the operator
   sees the relationship at a glance. The vertical spacing comes from the
   surrounding field stack. */
.board-settings__detail {
  display: flex;
  align-items: center;
  gap: 6px;
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

.board-settings__coord-row {
  display: flex;
  align-items: flex-end;
  gap: var(--dimension-3);
}

.board-settings__pick-btn {
  flex-shrink: 0;
  gap: var(--dimension-2);
}

.board-settings__pick-btn svg {
  flex-shrink: 0;
}

/* Vertical stacks (former space-y utilities). __form must come after
   __subsection so its 10px gap wins between subsections, matching the old
   utility specificity. */
.board-settings__form > * + * {
  margin-top: 10px;
}

.board-settings__stack > * + * {
  margin-top: var(--dimension-4);
}

.board-settings__field > * + * {
  margin-top: var(--dimension-3);
}

.board-settings__row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.board-settings__input-row {
  display: flex;
  align-items: center;
  gap: 5px;
}

.board-settings__num {
  width: 100px;
}

.board-settings__num--full {
  width: 100%;
}

.board-settings__unit {
  flex-shrink: 0;
  font-size: var(--font-size-large);
  color: var(--text-muted);
}

.board-settings__coord-grid {
  display: grid;
  flex: 1 1 0%;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--dimension-4);
}

.board-settings__grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--dimension-4);
}

.board-settings__toggle-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.board-settings__toggle {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.board-settings__toggle-label {
  font-size: var(--font-size-large);
}

.board-settings__error {
  font-size: var(--font-size-normal);
  color: var(--color-light-red-40);
}

.board-settings__perm-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.board-settings__perm-table {
  width: 100%;
  font-size: var(--font-size-large);
}

.board-settings__perm-head-row {
  border-bottom: 1px solid var(--border);
}

.board-settings__perm-th {
  padding: var(--dimension-3) var(--dimension-4);
  font-size: var(--font-size-large);
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  text-align: left;
}

.board-settings__perm-th--center {
  width: 80px;
  text-align: center;
}

.board-settings__perm-body tr + tr {
  border-top: 1px solid var(--border);
}

.board-settings__perm-row:hover {
  background: var(--bg-hover);
}

.board-settings__perm-td {
  padding: var(--dimension-3) var(--dimension-4);
}

.board-settings__perm-td--name {
  font-weight: 500;
  color: var(--text);
}

.board-settings__perm-td--center {
  text-align: center;
}

.board-settings__perm-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.board-settings__perm-wildcard {
  font-size: 10px;
  color: var(--text-muted);
}

.board-settings__perm-empty {
  padding: var(--dimension-8) 0;
  font-size: var(--font-size-large);
  color: var(--text-muted);
  text-align: center;
}

.board-settings__perm-note {
  margin-top: var(--dimension-5);
  padding: 0 var(--dimension-3);
  font-size: var(--font-size-large);
  color: var(--text-muted);
}
</style>
