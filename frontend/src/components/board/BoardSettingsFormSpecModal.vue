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
            <div v-if="activeTab === 'general'" ref="generalFormEl" class="board-settings__form">
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

              <div v-if="templatePreview" class="board-settings__template-preview">
                <span class="board-settings__template-preview-label">{{
                  _t('Hover preview:')
                }}</span>
                <code>{{ templatePreview }}</code>
              </div>

              <!-- Background (static only) -->
              <div
                v-if="form.map_type === 'static'"
                class="board-settings__type-section board-settings__stack"
              >
                <p class="section-title">{{ _t('Background') }}</p>
                <div class="board-settings__field">
                  <CmkLabel>{{ _t('Background image') }}</CmkLabel>
                  <BackgroundImageUpload
                    v-model:pending-file="pendingBgFile"
                    v-model:pending-remove="pendingBgRemove"
                    :model-value="form.background_image"
                    :pending-preview-url="pendingBgPreviewUrl"
                  />
                </div>
                <div class="board-settings__field">
                  <CmkLabel>{{ _t('Background color') }}</CmkLabel>
                  <ColorInput
                    v-model="form.background_color"
                    :enable-label="_t('Use color')"
                    default-color="#1f2937"
                  />
                </div>
              </div>

              <!-- Worldmap settings -->
              <div
                v-if="form.map_type === 'worldmap'"
                class="board-settings__type-section board-settings__stack"
              >
                <p class="section-title">{{ _t('Map view') }}</p>
                <div class="board-settings__coord-row">
                  <div class="board-settings__coord-grid">
                    <div class="board-settings__field">
                      <CmkLabel>{{ _t('Latitude') }}</CmkLabel>
                      <NumberInput
                        v-model="form.worldmap_lat"
                        step="any"
                        :precision="10"
                        class="board-settings__num board-settings__num--full"
                      />
                    </div>
                    <div class="board-settings__field">
                      <CmkLabel>{{ _t('Longitude') }}</CmkLabel>
                      <NumberInput
                        v-model="form.worldmap_lng"
                        step="any"
                        :precision="10"
                        class="board-settings__num board-settings__num--full"
                      />
                    </div>
                    <div class="board-settings__field">
                      <CmkLabel
                        :help="
                          _t(
                            'Pan/zoom the map first, then reopen settings to capture the current view.'
                          )
                        "
                        >{{ _t('Zoom') }}</CmkLabel
                      >
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
                    :title="_t('Closes settings and switches the map to picker mode.')"
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
                    <span>{{ _t('Pick from map') }}</span>
                  </CmkButton>
                </div>
                <div class="board-settings__field">
                  <CmkLabel>{{ _t('Tile server URL') }}</CmkLabel>
                  <CmkInput
                    v-model="form.worldmap_tile_url"
                    :placeholder="_t('https://%{s}.tile.openstreetmap.org/%{z}/%{x}/%{y}.png')"
                    field-size="FILL"
                  />
                </div>
                <div class="board-settings__field">
                  <CmkLabel>{{ _t('Map saturation (%)') }}</CmkLabel>
                  <NumberInput
                    v-model="form.worldmap_tile_saturate"
                    :min="0"
                    :max="100"
                    :step="5"
                    :placeholder="_t('100 (default)')"
                    class="board-settings__num board-settings__num--full"
                  />
                </div>

                <!-- Automap: dynamically populate the board from
                                 host geo-coords (orbvis_lat/orbvis_lng labels
                                 or LAT/LONG custom variables). Mirrors NagVis
                                 automap with lat/lng. -->
                <div class="board-settings__subsection board-settings__field">
                  <CmkLabel
                    :help="
                      _t(
                        'Hosts are auto-discovered from monitoring data via orbvis_lat/orbvis_lng labels or LAT/LONG custom variables. They show up alongside any objects you place manually.'
                      )
                    "
                    >{{ _t('Automap source') }}</CmkLabel
                  >
                  <CmkDropdown
                    :selected-option="form.worldmap_auto_source || ''"
                    :options="worldmapAutoSourceOptions"
                    :width="'fill'"
                    :label="_t('Automap source')"
                    @update:selected-option="
                      form.worldmap_auto_source = ($event ?? '') as typeof form.worldmap_auto_source
                    "
                  />
                  <div
                    v-if="
                      form.worldmap_auto_source === 'hostgroup' ||
                      form.worldmap_auto_source === 'servicegroup'
                    "
                    class="board-settings__field"
                  >
                    <CmkLabel> {{ _t('Group name') }}<CmkLabelRequired space="before" /> </CmkLabel>
                    <CmkInput
                      v-model="form.worldmap_auto_filter_value"
                      :placeholder="_t('group name (e.g. &quot;muc&quot;)')"
                      field-size="FILL"
                      :class="{
                        'orb-input-invalid': saveAttempted && !form.worldmap_auto_filter_value
                      }"
                    />
                  </div>
                </div>
              </div>

              <!-- Flow settings: served as a FormSpec so titles/help
                         and the Integer-input look match the rest of the
                         Checkmk FormSpec UI. -->
              <FormEdit
                v-if="form.map_type === 'flow' && flowViewFormSchema"
                v-model:data="flowViewFormSpecData"
                :spec="flowViewFormSchema"
                :backend-validation="[]"
              />

              <!-- Radar settings -->
              <div
                v-if="form.map_type === 'radar'"
                class="board-settings__type-section board-settings__stack"
              >
                <p class="section-title">{{ _t('Filter') }}</p>
                <div class="board-settings__grid-2">
                  <div class="board-settings__field">
                    <CmkLabel>{{ _t('Filter type') }}</CmkLabel>
                    <CmkDropdown
                      :selected-option="form.radar_filter || null"
                      :options="radarFilterOptions"
                      :width="'fill'"
                      :label="_t('Filter type')"
                      @update:selected-option="form.radar_filter = $event ?? ''"
                    />
                  </div>
                  <div
                    v-if="form.radar_filter === 'hostgroup' || form.radar_filter === 'servicegroup'"
                    class="board-settings__field"
                  >
                    <CmkLabel
                      :help="
                        _t(
                          'Hosts (or hosts hosting a service) belonging to this Checkmk group are pulled live from the connection. Group must exist in Checkmk WATO.'
                        )
                      "
                      >{{ _t('Group name') }}</CmkLabel
                    >
                    <CmkDropdown
                      :selected-option="form.radar_filter_value || null"
                      :options="radarGroupOptions"
                      :width="'fill'"
                      :label="_t('Group name')"
                      :input-hint="_t('Group name')"
                      :required="true"
                      :form-validation="saveAttempted && !form.radar_filter_value"
                      :no-elements-text="
                        form.radar_filter === 'hostgroup'
                          ? _t('No host groups configured in this site')
                          : _t('No service groups configured in this site')
                      "
                      @update:selected-option="form.radar_filter_value = $event ?? ''"
                    />
                  </div>
                </div>
              </div>

              <!-- Folder tree settings -->
              <div
                v-if="form.map_type === 'foldertree'"
                class="board-settings__type-section board-settings__stack"
              >
                <p class="section-title">{{ _t('Folder tree') }}</p>
                <div class="board-settings__grid-2">
                  <div class="board-settings__field">
                    <CmkLabel
                      :help="
                        _t(
                          'Show only this folder and below. Empty = whole tree. Accepts a folder path or its stable id.'
                        )
                      "
                      >{{ _t('Root folder') }}</CmkLabel
                    >
                    <CmkDropdown
                      :selected-option="form.ft_root_folder"
                      :options="ftRootFolderOptions"
                      :width="'fill'"
                      :label="_t('Root folder')"
                      @update:selected-option="form.ft_root_folder = $event ?? ''"
                    />
                  </div>
                  <div class="board-settings__field">
                    <CmkLabel
                      :help="_t('How many folder levels are expanded when the board opens.')"
                      >{{ _t('Auto-expand depth') }}</CmkLabel
                    >
                    <NumberInput
                      v-model="form.ft_default_expand_depth"
                      min="0"
                      max="20"
                      class="board-settings__num"
                    />
                  </div>
                </div>
                <div class="board-settings__field">
                  <CmkLabel :help="_t('Which presentation the board opens in by default.')">{{
                    _t('Default view')
                  }}</CmkLabel>
                  <CmkDropdown
                    :selected-option="form.ft_default_view"
                    :options="ftDefaultViewOptions"
                    :width="'fill'"
                    :label="_t('Default view')"
                    @update:selected-option="
                      form.ft_default_view = ($event as 'list' | 'map') ?? 'list'
                    "
                  />
                </div>
                <div class="board-settings__field">
                  <CmkLabel
                    :help="
                      _t(
                        'Distributed monitoring: limit the tree to these sites. None selected = all sites.'
                      )
                    "
                    >{{ _t('Sites') }}</CmkLabel
                  >
                  <FtSitesSelect v-model="ftSites" :options="siteOptions" />
                </div>
                <div class="board-settings__toggle-list">
                  <div class="board-settings__toggle">
                    <CmkSwitch v-model="form.ft_show_empty_folders" />
                    <span
                      class="board-settings__toggle-label"
                      @click="form.ft_show_empty_folders = !form.ft_show_empty_folders"
                      >{{ _t('Show empty folders') }}</span
                    >
                  </div>
                  <div class="board-settings__toggle">
                    <CmkSwitch v-model="form.ft_show_services" />
                    <span
                      class="board-settings__toggle-label"
                      @click="form.ft_show_services = !form.ft_show_services"
                      >{{ _t('Expand hosts to their services') }}</span
                    >
                  </div>
                  <div class="board-settings__toggle">
                    <CmkSwitch v-model="form.ft_problems_only" />
                    <span
                      class="board-settings__toggle-label"
                      @click="form.ft_problems_only = !form.ft_problems_only"
                      >{{ _t('Show only folders/hosts with problems') }}</span
                    >
                  </div>
                  <div v-if="form.ft_problems_only" class="board-settings__field">
                    <CmkLabel
                      :help="
                        _t(
                          'On typical sites almost every host carries some WARNING service — narrowing to critical keeps the problem filter meaningful.'
                        )
                      "
                      >{{ _t('Problem severity') }}</CmkLabel
                    >
                    <CmkDropdown
                      :selected-option="form.ft_problems_severity"
                      :options="ftProblemsSeverityOptions"
                      :width="'fill'"
                      :label="_t('Problem severity')"
                      @update:selected-option="
                        form.ft_problems_severity = ($event as 'any' | 'critical') ?? 'any'
                      "
                    />
                  </div>
                  <div class="board-settings__toggle">
                    <CmkSwitch v-model="form.ft_only_hard_states" />
                    <span
                      class="board-settings__toggle-label"
                      @click="form.ft_only_hard_states = !form.ft_only_hard_states"
                      >{{ _t('Use hard states only') }}</span
                    >
                  </div>
                </div>
              </div>

              <ul v-if="errorMessages.length" class="board-settings__errors">
                <li v-for="(msg, i) in errorMessages" :key="i">{{ msg }}</li>
              </ul>
            </div>

            <!-- Permissions -->
            <div v-else-if="activeTab === 'permissions'">
              <!-- Inside a Checkmk deployment, CMK role permissions
                         (orbvis.see/edit) are the source of truth, not the
                         OrbVis role table. Show a read-only summary plus a
                         deep-link to WATO instead. -->
              <div v-if="isCmkDeployment" class="board-settings__perm-cmk">
                <p class="board-settings__perm-cmk-intro">
                  {{
                    _t(
                      'Board view and edit are gated by Checkmk role permissions (orbvis.see, orbvis.edit). Manage them in Checkmk WATO.'
                    )
                  }}
                </p>
                <CmkButton variant="secondary" @click="openCmkRoles">
                  {{ _t('Open role editor in Checkmk') }}
                </CmkButton>
              </div>
              <div v-else-if="permLoading" class="board-settings__perm-loading">
                <CmkLoading />
              </div>
              <div v-else>
                <table class="board-settings__perm-table">
                  <thead>
                    <tr class="board-settings__perm-head-row">
                      <th class="board-settings__perm-th">
                        {{ _t('Role') }}
                      </th>
                      <th class="board-settings__perm-th board-settings__perm-th--center">
                        {{ _t('View') }}
                      </th>
                      <th class="board-settings__perm-th board-settings__perm-th--center">
                        {{ _t('Edit') }}
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
                            :title="_t('Granted via wildcard rule')"
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
                            :title="_t('Granted via wildcard rule')"
                            >*</span
                          >
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p v-if="!permRoles.length" class="board-settings__perm-empty">
                  {{ _t('No roles defined yet') }}
                </p>
                <p class="board-settings__perm-note">
                  *
                  {{
                    _t(
                      'Permissions marked with * apply via a wildcard rule and cannot be changed here.'
                    )
                  }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Hidden on narrow viewports where two columns don't fit. -->
        <aside v-if="showPreview" class="board-settings__preview">
          <span class="board-settings__preview-label">{{ _t('Live preview') }}</span>
          <div class="board-settings__preview-stage">
            <iframe
              ref="previewIframe"
              :key="previewKey"
              :src="previewUrl"
              class="board-settings__preview-frame"
              :title="_t('Live preview')"
              @load="onPreviewLoaded"
            />
            <div v-if="previewLoading" class="board-settings__preview-loading">
              <CmkLoading />
            </div>
          </div>
        </aside>
      </div>

      <div class="board-settings__footer">
        <CmkButton v-if="isDirty" variant="optional" :disabled="saving" @click="resetChanges">
          {{ _t('Reset') }}
        </CmkButton>
        <CmkButton variant="optional" @click="togglePreview">
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
            style="margin-right: 6px"
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
          {{ showPreview ? _t('Hide preview') : _t('Show preview') }}
        </CmkButton>
        <span class="board-settings__footer-spacer" />
        <CmkButton v-if="auth.canCreateBoards" variant="danger" @click="deleteBoard">
          {{ _t('Delete board…') }}
        </CmkButton>
        <CmkButton variant="secondary" @click="requestClose">
          {{ _t('Close') }}
        </CmkButton>
        <CmkButton
          variant="primary"
          :disabled="saving || !isDirty || (saveAttempted && !customSectionValid)"
          :title="saveButtonTooltip"
          @click="save"
        >
          {{ saving ? _t('Saving…') : _t('Save') }}
        </CmkButton>
      </div>
    </div>
  </CmkSlideInDialog>
  <OrbUnsavedChangesDialog
    :open="discardDialogOpen"
    @confirm="confirmDiscard"
    @cancel="cancelDiscard"
  />
  <OrbConfirmDialog
    :open="deleteDialogOpen"
    variant="error"
    :title="
      _t('Delete board &quot;%{name}&quot;?', { name: props.board.alias || props.board.name })
    "
    :message="
      _t(
        'This permanently removes the board configuration. Existing object data on other boards is unaffected.'
      )
    "
    :confirm-label="_t('Delete board…')"
    confirm-variant="danger"
    @confirm="confirmDelete"
    @cancel="deleteDialogOpen = false"
  />
</template>

<script setup lang="ts">
import CmkLabelRequired from '@cmk/components/user-input/CmkLabelRequired.vue'
import FormEdit from '@cmk/form/FormEdit.vue'
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch'
import type {
  ValidationMessage,
  VueFormspecComponents
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue'

import ColorInput from '@/components/ColorInput.vue'
import NumberInput from '@/components/NumberInput.vue'
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import OrbUnsavedChangesDialog from '@/components/OrbUnsavedChangesDialog.vue'
import CmkButton from '@/components/cmk/CmkButton'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkLabel from '@/components/cmk/CmkLabel'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkSlideInDialog from '@/components/cmk/CmkSlideInDialog'
import CmkSwitch from '@/components/cmk/CmkSwitch'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { ApiError, boardsApi, boardsApiFormSpec, connectionsApi, rolesApi } from '@/api/client'
import { orbFormComponents } from '@/composables/orbFormComponents'
import { useDictionaryGroupAttrs } from '@/composables/useDictionaryGroupAttrs'
import { useRadarGroups } from '@/composables/useRadarGroups'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import type {
  BoardObject,
  BoardRead,
  ConnectionConfig,
  FlowView,
  FolderTreeView,
  ObjectState,
  PermissionRead,
  RadarView,
  RoleRead,
  WorldmapView
} from '@/types/api'
import { openUrl } from '@/utils/boardNavigation'
import { toFormValidation } from '@/utils/formValidation'
import { PREVIEW_EDIT, PREVIEW_READY } from '@/utils/previewBridge'
import { interpolateTemplate } from '@/utils/template'
import usei18n from '@/vendor/cmk/lib/i18n'
import { useDebounceFn } from '@/vendor/cmk/lib/useDebounce'

import BackgroundImageUpload from './BackgroundImageUpload.vue'
import FtSitesSelect from './FtSitesSelect.vue'

const props = defineProps<{
  board: BoardRead
  worldmapView?: { lat: number; lng: number; zoom: number } | null
  parentMapSize?: { width: number; height: number } | null
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
    // Private-Mode / Storage voll – Toggle wirkt nur in dieser Sitzung.
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
      // Pick liefert Parent-Canvas-Werte: Preview-Zoom-Kompensation
      // wieder aktivieren, sobald der watch worldmapViewEdited gesetzt hat.
      nextTick(() => {
        worldmapViewEdited.value = false
      })
    }
  })
}
function onSlideInClose() {
  // Während des Pickens schließt das Slide-In nur visuell — Esc/Backdrop sollen
  // den Pick nicht beenden und auch nicht den Discard-Dialog auslösen.
  if (isPickingView.value) return
  requestClose()
}

const { _t } = usei18n()
const auth = useAuthStore()
const boardsStore = useBoardsStore()
const toast = useToast()

const isCmkDeployment = computed(() => auth.ssoActive || auth.isCheckmkDeployment)

// Picked up by FormOrbHostAutocomplete via inject.
const currentConnectionId = computed(
  () => (formSpecData.value.connection_id as string | undefined) ?? props.board.connection_id
)
provide('orbConnectionId', currentConnectionId)
// Deleting a board and managing its permissions are admin-only; a non-admin
// with edit rights may change settings but not remove or re-share the board.
const tabs = computed<{ id: 'general' | 'permissions'; label: string }[]>(() =>
  auth.isAdmin
    ? [
        { id: 'general', label: _t('Settings') },
        { id: 'permissions', label: _t('Board Permissions') }
      ]
    : [{ id: 'general', label: _t('Settings') }]
)
const activeTab = ref<'general' | 'permissions'>('general')

// Same OMD site as the OrbVis path prefix; mirrors stores/auth.ts.
const cmkRolesUrl = computed(() => {
  const m = window.location.pathname.match(/^(\/[^/]+)\/orbvis/)
  return m ? `${m[1]}/check_mk/wato.py?mode=roles` : '/check_mk/wato.py?mode=roles'
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
  ft_root_folder: ftv?.root_folder ?? '',
  ft_default_view: (ftv?.default_view ?? 'list') as 'list' | 'map',
  ft_default_expand_depth: ftv?.default_expand_depth ?? 1,
  ft_show_services: ftv?.show_services ?? false,
  ft_show_empty_folders: ftv?.show_empty_folders ?? true,
  ft_problems_only: ftv?.problems_only ?? false,
  ft_problems_severity: (ftv?.problems_severity ?? 'any') as 'any' | 'critical',
  ft_only_hard_states: ftv?.only_hard_states ?? false,
  ft_sites: (ftv?.sites ?? []).join(', '),
  hover_template: props.board.hover_template ?? '',
  context_template: props.board.context_template ?? '',
  background_image: props.board.background_image ?? '',
  background_color: props.board.background_color ?? ''
})

const connections = ref<ConnectionConfig[]>([])
const saving = ref(false)

type Schema = NonNullable<VueFormspecComponents['components']>
initializeComponentRegistry(orbFormComponents)
const formSchema = ref<Schema | null>(null)
const schemaLoading = ref(true)
const generalFormEl = ref<HTMLElement | null>(null)
useDictionaryGroupAttrs(
  generalFormEl,
  () => (formSchema.value as { elements?: { group?: { key?: string | null } | null }[] })?.elements
)
// Optional fields are omitted entirely when the board has no value, so the
// FormSpec dispatcher renders them as un-checked (= inherit global defaults);
// '' / null would leave the checkbox enabled with an empty value, which reads
// as "override with nothing".
// click_action is a BooleanChoice in the FormSpec but 'link'|'none' on the
// wire; rotation_interval is a CascadingSingleChoice but a flat int on the
// wire. Both are flattened on save() below.
const rotationInterval = props.board.rotation_interval ?? 0
const formSpecDataInitial: Record<string, unknown> = {
  alias: props.board.alias,
  connection_id: props.board.connection_id,
  rotation_interval: rotationInterval > 0 ? ['every', rotationInterval] : ['off', null],
  click_action: props.board.click_action !== 'none',
  render_mode: props.board.render_mode ?? 'default',
  default_z: props.board.default_z ?? 1,
  show_in_lists: props.board.show_in_lists !== false
}
if (props.board.icon_size != null) formSpecDataInitial.icon_size = props.board.icon_size
if (props.board.hover_template) formSpecDataInitial.hover_template = props.board.hover_template
if (props.board.context_template)
  formSpecDataInitial.context_template = props.board.context_template
const formSpecData = ref<Record<string, unknown>>(formSpecDataInitial)

// Separate FormSpec data bag for the Flow `view` block. Same omit-when-null
// convention as the metadata schema: a missing key reads as "inherit", which
// matches FlowView's `None = use default` semantics.
const flowViewFormSpecDataInitial: Record<string, unknown> = {}
if (fv?.root) flowViewFormSpecDataInitial.root = fv.root
if (fv?.child_layers != null) flowViewFormSpecDataInitial.child_layers = fv.child_layers
if (fv?.parent_layers != null) flowViewFormSpecDataInitial.parent_layers = fv.parent_layers
if (fv?.top_affected_hosts != null)
  flowViewFormSpecDataInitial.top_affected_hosts = fv.top_affected_hosts
if (fv?.max_services_per_host != null)
  flowViewFormSpecDataInitial.max_services_per_host = fv.max_services_per_host
const flowViewFormSpecData = ref<Record<string, unknown>>(flowViewFormSpecDataInitial)
const flowViewFormSchema = ref<Schema | null>(null)

const templatePreview = computed(() => {
  const tpl = (formSpecData.value.hover_template as string | undefined)?.trim()
  if (!tpl) return ''
  const sampleObject: BoardObject = {
    id: 'demo',
    type: 'service',
    host_name: 'db-prod-01',
    service_description: 'HTTP',
    x: 0,
    y: 0,
    z: 0,
    url_target: '_self'
  }
  const sampleState: ObjectState = {
    object_id: 'demo',
    type: 'service',
    state: 'CRITICAL',
    output: 'TCP connection refused',
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false
  }
  try {
    return interpolateTemplate(tpl, sampleObject, sampleState)
  } catch {
    return ''
  }
})

const boardTitle = computed(() => {
  const alias = form.value.alias || props.board.name
  const head = _t('Board Settings') + ' — ' + alias
  return alias === props.board.name ? head : `${head} · ${props.board.name}`
})

function openCmkRoles() {
  openUrl(cmkRolesUrl.value, '_blank')
}

function openBoard() {
  emit('close')
  window.location.hash = `#/boards/${encodeURIComponent(props.board.name)}`
}

const worldmapAutoSourceOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: _t('None — manual placement only') },
    { name: 'all_hosts', title: _t('All hosts with geo coordinates') },
    { name: 'hostgroup', title: _t('Hosts in host group…') },
    { name: 'servicegroup', title: _t('Hosts hosting a service in service group…') }
  ]
}))
const radarFilterOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'hostgroup', title: _t('Host group') },
    { name: 'servicegroup', title: _t('Service group') },
    { name: 'all_hosts', title: _t('All hosts') },
    { name: 'all_services', title: _t('All services') }
  ]
}))
const saveError = ref('')

const folderOptions = ref<{ path: string; title: string }[]>([])
const ftDefaultViewOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'list', title: _t('List (tree)') },
    { name: 'map', title: _t('Map (treemap)') }
  ]
}))

const ftProblemsSeverityOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'any', title: _t('Any problem (incl. WARNING)') },
    { name: 'critical', title: _t('Only critical & down') }
  ]
}))
const ftRootFolderOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: _t('(all folders)') },
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

const { names: radarGroupNames } = useRadarGroups(form, () => auth.accessToken)

const radarGroupOptions = computed(() => ({
  type: 'filtered' as const,
  suggestions: radarGroupNames.value.map((name) => ({ name, title: name }))
}))

const saveAttempted = ref(false)
const formBackendValidation = ref<ValidationMessage[]>([])

const customMissingFields = computed<string[]>(() => {
  const missing: string[] = []
  if (
    form.value.map_type === 'radar' &&
    (form.value.radar_filter === 'hostgroup' || form.value.radar_filter === 'servicegroup') &&
    !form.value.radar_filter_value
  ) {
    missing.push(_t('Group name'))
  }
  if (
    form.value.map_type === 'worldmap' &&
    (form.value.worldmap_auto_source === 'hostgroup' ||
      form.value.worldmap_auto_source === 'servicegroup') &&
    !form.value.worldmap_auto_filter_value
  ) {
    missing.push(_t('Group name'))
  }
  return missing
})
const customSectionValid = computed(() => customMissingFields.value.length === 0)

const errorMessages = computed<string[]>(() => {
  const out: string[] = []
  if (saveAttempted.value) {
    for (const f of customMissingFields.value) {
      out.push(_t('%{field} is required.', { field: f }))
    }
  }
  if (saveError.value) out.push(saveError.value)
  return out
})

async function save() {
  saveAttempted.value = true
  if (!customSectionValid.value) {
    return
  }
  saving.value = true
  saveError.value = ''
  formBackendValidation.value = []
  try {
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
    let view: Record<string, unknown> = buildViewFromForm()
    if (form.value.map_type === 'flow') {
      // Preserve service_layout / positions written by the preview iframe.
      const fresh = await boardsApi.get(props.board.name, auth.accessToken!)
      const freshFlow = fresh.view?.type === 'flow' ? fresh.view : null
      view = {
        ...view,
        service_layout: freshFlow?.service_layout ?? null,
        positions: freshFlow?.positions ?? {}
      }
    }
    const fs = formSpecData.value as Record<string, unknown>
    const rotRaw = fs.rotation_interval
    let rotationInt = 0
    if (Array.isArray(rotRaw) && rotRaw.length === 2) {
      const [choice, value] = rotRaw
      if (choice === 'every' && typeof value === 'number') rotationInt = value
    }
    const updated = await boardsApi.update(
      props.board.name,
      {
        alias: (fs.alias as string) ?? props.board.alias,
        connection_id: (fs.connection_id as string) ?? props.board.connection_id,
        icon_size: (fs.icon_size as number | null | undefined) ?? null,
        rotation_interval: rotationInt,
        click_action: (fs.click_action as boolean | undefined) === false ? 'none' : 'link',
        render_mode: (fs.render_mode as 'default' | 'nagvis_classic' | undefined) ?? 'default',
        default_z: (fs.default_z as number | undefined) ?? props.board.default_z ?? 1,
        show_in_lists: (fs.show_in_lists as boolean | undefined) ?? true,
        background_image: form.value.background_image || null,
        background_color: form.value.background_color || null,
        // Presentation slide design (elements, theme, size, background) is
        // owned and autosaved by the canvas — omit ``view`` here so saving
        // board metadata never clobbers the slide.
        ...(form.value.map_type === 'presentation' ? {} : { view }),
        hover_template: ((fs.hover_template as string) ?? '') || null,
        context_template: ((fs.context_template as string) ?? '') || null
      },
      auth.accessToken!,
      localVersion.value
    )
    localVersion.value = updated.version ?? localVersion.value
    if (boardsStore.currentBoard?.name === updated.name) {
      boardsStore.currentBoard = updated
    }
    initialSnapshot.value = JSON.stringify({
      form: form.value,
      formSpec: formSpecData.value,
      flowView: flowViewFormSpecData.value
    })
    if (pendingBgFile.value || pendingBgRemove.value) {
      boardsStore.bumpBgRefreshTick(props.board.name)
    }
    pendingBgFile.value = null
    pendingBgRemove.value = false
    saveAttempted.value = false
    toast.success(_t('Board settings saved'), {
      label: _t('Open board'),
      onClick: openBoard
    })
    previewLoading.value = true
    previewKey.value++
    emit('updated')
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status === 409) {
      saveError.value = _t(
        'Board changed elsewhere — close and reopen to apply your edit on top of the latest version.'
      )
    } else if (e instanceof ApiError && e.status === 422) {
      const detail = (e.detail as { detail?: unknown } | null)?.detail
      const parsed = toFormValidation(detail, new Set(Object.keys(formSpecData.value)))
      if (parsed) {
        formBackendValidation.value = parsed.messages
        saveError.value = parsed.stray.map((m) => m.message).join(' ')
      } else {
        saveError.value = e.message
      }
    } else {
      saveError.value = e instanceof Error ? e.message : 'An error occurred'
    }
  } finally {
    saving.value = false
  }
}

// ── Permissions ────────────────────────────────────────────────────────────
const permRoles = ref<RoleRead[]>([])
const permLoading = ref(false)
// Draft: key = `${role_id}-${act}`, value = desired checked state (undefined = use server state)
const permDraft = reactive(new Map<string, boolean>())

// Snapshot the initial form state so we can disable Save when nothing
// changed and confirm before discarding edits on cancel/close. Re-taken
// after FormEdit settles in onMounted because the visitor may normalise
// formSpecData on first render (e.g. fill optional fields with defaults),
// which would otherwise look like a user edit.
// Baseline reflektiert die Disk-Config (nicht die via worldmapView vorbefüllten
// Form-Werte), sodass isDirty nach Rechtsklick-Prefill korrekt anschlägt.
function snapshotForm(): Record<string, unknown> {
  if (!wmv) return { ...form.value }
  return {
    ...form.value,
    worldmap_lat: wmv.lat,
    worldmap_lng: wmv.lng,
    worldmap_zoom: wmv.zoom
  }
}
const initialSnapshot = ref(
  JSON.stringify({
    form: snapshotForm(),
    formSpec: formSpecData.value,
    flowView: flowViewFormSpecData.value
  })
)
// Tracks the persisted board version so subsequent saves use the
// up-to-date If-Match header instead of the now-stale props value.
const localVersion = ref<number | null>(props.board.version ?? null)
// Background image is staged here and only uploaded/removed on save, so closing
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
const isDirty = computed(
  () =>
    JSON.stringify({
      form: form.value,
      formSpec: formSpecData.value,
      flowView: flowViewFormSpecData.value
    }) !== initialSnapshot.value ||
    permDraft.size > 0 ||
    pendingBgFile.value !== null ||
    pendingBgRemove.value
)

const saveButtonTooltip = computed(() => {
  if (saving.value) return ''
  if (!isDirty.value) return _t('No changes to save')
  if (saveAttempted.value && !customSectionValid.value)
    return _t('Fix the highlighted fields to save')
  return _t('Save (%{shortcut})', { shortcut: saveShortcutHint })
})

const discardDialogOpen = ref(false)
function requestClose() {
  if (isDirty.value) {
    discardDialogOpen.value = true
    return
  }
  emit('close')
}
function confirmDiscard() {
  discardDialogOpen.value = false
  emit('close')
}
function cancelDiscard() {
  discardDialogOpen.value = false
}

function resetChanges() {
  const snapshot = JSON.parse(initialSnapshot.value) as {
    form: typeof form.value
    formSpec: Record<string, unknown>
    flowView: Record<string, unknown>
  }
  form.value = snapshot.form
  formSpecData.value = snapshot.formSpec
  flowViewFormSpecData.value = snapshot.flowView
  permDraft.clear()
  pendingBgFile.value = null
  pendingBgRemove.value = false
  saveAttempted.value = false
  formBackendValidation.value = []
  saveError.value = ''
}

// Show ⌘ on macOS, Ctrl elsewhere.
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '')
const saveShortcutHint = isMac ? '⌘S' : 'Ctrl+S'

function handleKeydown(e: KeyboardEvent) {
  const modifier = isMac ? e.metaKey : e.ctrlKey
  if (!modifier) return
  if (e.key === 's' || e.key === 'S' || e.key === 'Enter') {
    e.preventDefault()
    if (!saving.value && isDirty.value && customSectionValid.value) save()
  }
}

const previewKey = ref(0)
const previewLoading = ref(true)
const previewIframe = ref<HTMLIFrameElement | null>(null)
const previewUrl = computed(
  () => `${window.location.pathname}#/boards/${encodeURIComponent(props.board.name)}?preview=1`
)

function buildViewFromForm(): Record<string, unknown> {
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
    const fvd = flowViewFormSpecData.value as Record<string, unknown>
    const rootRaw = (fvd.root as string | undefined)?.trim()
    return {
      type: 'flow',
      root: rootRaw || null,
      child_layers: (fvd.child_layers as number | null | undefined) ?? null,
      parent_layers: (fvd.parent_layers as number | null | undefined) ?? null,
      top_affected_hosts: (fvd.top_affected_hosts as number | null | undefined) ?? null,
      max_services_per_host: (fvd.max_services_per_host as number | null | undefined) ?? null
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
      problems_severity: form.value.ft_problems_severity,
      only_hard_states: form.value.ft_only_hard_states,
      sites: form.value.ft_sites
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    }
  }
  return { type: form.value.map_type }
}

function buildPreviewPatch(): Record<string, unknown> {
  const fs = formSpecData.value as Record<string, unknown>
  return {
    alias: (fs.alias as string) ?? props.board.alias,
    icon_size: (fs.icon_size as number | null | undefined) ?? null,
    hover_template: (fs.hover_template as string) ?? '',
    context_template: (fs.context_template as string) ?? '',
    background_color: form.value.background_color || null,
    // Presentation slides are designed on the canvas, not here — patching a
    // metadata-only ``view`` would blank the slide in the preview iframe.
    ...(form.value.map_type === 'presentation' ? {} : { view: buildViewFromForm() })
  }
}

const worldmapViewEdited = ref(false)
watch(
  () => [form.value.worldmap_lat, form.value.worldmap_lng, form.value.worldmap_zoom] as const,
  ([lat, lng, zoom]) => {
    worldmapViewEdited.value = true
    if (form.value.map_type === 'worldmap') {
      emit('worldmapViewChange', { lat, lng, zoom })
    }
  }
)

// External re-apply: when the parent re-sets ``worldmapView`` (e.g. via the
// "save current view as default" right-click action on the parent canvas) and
// the modal is already open, ``initWorldmapCoords`` has long since run — we
// must reflect the new view into the form so the preview repaints.
watch(
  () => props.worldmapView,
  (next) => {
    if (!next) return
    if (
      form.value.worldmap_lat === next.lat &&
      form.value.worldmap_lng === next.lng &&
      form.value.worldmap_zoom === next.zoom
    ) {
      return
    }
    form.value.worldmap_lat = next.lat
    form.value.worldmap_lng = next.lng
    form.value.worldmap_zoom = next.zoom
  }
)

function postPreviewPatch() {
  const win = previewIframe.value?.contentWindow
  if (!win) return
  const patch = buildPreviewPatch()
  // Solange der User keine view-Felder editiert hat, rauszoomen, bis der
  // Preview den gleichen geographischen Bereich wie das Eltern-Board zeigt.
  if (
    form.value.map_type === 'worldmap' &&
    !worldmapViewEdited.value &&
    props.parentMapSize &&
    previewIframe.value
  ) {
    const previewW = previewIframe.value.getBoundingClientRect().width
    const parentW = props.parentMapSize.width
    if (previewW > 0 && parentW > 0) {
      const view = patch.view as Record<string, unknown> & { zoom: number }
      view.zoom = view.zoom + Math.log2(previewW / parentW)
    }
  }
  win.postMessage({ source: PREVIEW_EDIT, patch }, window.location.origin)
}

const schedulePreviewPost = useDebounceFn(postPreviewPatch, 120)

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

function onPreviewLoaded() {
  previewLoading.value = false
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

watch([form, formSpecData, flowViewFormSpecData], schedulePreviewPost, { deep: true })
watch([pendingBgPreviewUrl, pendingBgRemove], postBgPatch)

const deleteDialogOpen = ref(false)
function deleteBoard() {
  deleteDialogOpen.value = true
}
async function confirmDelete() {
  deleteDialogOpen.value = false
  const label = props.board.alias || props.board.name
  try {
    await boardsApi.delete(props.board.name, auth.accessToken!)
    toast.success(_t('Board "%{name}" deleted', { name: label }))
    emit('updated')
    emit('close')
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : 'An error occurred'
  }
}

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
  const flowSchemaPromise =
    form.value.map_type === 'flow'
      ? boardsApiFormSpec.getFlowViewSchema(auth.accessToken!).catch((): null => null)
      : Promise.resolve(null)
  // connections.list and roles are admin-only; a non-admin editor's 403s must
  // not reject this Promise.all (would leave schemaLoading stuck → spinner).
  const [bs, spec, flowSpec] = await Promise.all([
    connectionsApi.list(auth.accessToken!).catch((): ConnectionConfig[] => []),
    boardsApiFormSpec.getMetadataSchema(auth.accessToken!).catch((): null => null),
    flowSchemaPromise,
    auth.isAdmin ? loadPermissions() : Promise.resolve()
  ])
  connections.value = bs
  void loadFolderOptions()
  void loadSiteOptions()
  schemaLoading.value = false
  if (spec) {
    // Drop metadata fields that have no effect for the board type: radar and
    // foldertree have no hover/context popups, and the foldertree has no
    // coordinate-positioned icons that icon-size / layer / rendering touch.
    const drop = new Set<string>()
    if (form.value.map_type === 'radar') {
      drop.add('hover_template').add('context_template')
    } else if (form.value.map_type === 'foldertree') {
      drop
        .add('icon_size')
        .add('default_z')
        .add('render_mode')
        .add('hover_template')
        .add('context_template')
    } else if (form.value.map_type === 'presentation') {
      // The presentation board has no coordinate-positioned icons, no
      // hover/context popups and no per-object click action — slide design
      // lives on the canvas. Keep only identification, connection, rotation
      // and show-in-lists here.
      drop
        .add('icon_size')
        .add('default_z')
        .add('render_mode')
        .add('hover_template')
        .add('context_template')
        .add('click_action')
    }
    if (drop.size) {
      const dict = spec as { elements?: { name: string }[] }
      if (Array.isArray(dict.elements)) {
        dict.elements = dict.elements.filter((el) => !drop.has(el.name))
      }
    }
    formSchema.value = spec as unknown as Schema
  }
  if (flowSpec) flowViewFormSchema.value = flowSpec as unknown as Schema
  // Wait for FormEdit's first render to normalise formSpecData, then
  // snapshot again so isDirty doesn't fire on the visitor's own defaults.
  await nextTick()
  initialSnapshot.value = JSON.stringify({
    form: snapshotForm(),
    formSpec: formSpecData.value,
    flowView: flowViewFormSpecData.value
  })
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('message', onPreviewReady)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('message', onPreviewReady)
})
</script>

<style scoped>
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

.board-settings__preview-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated, var(--bg-hover));
  border: 1px solid var(--border);
  border-radius: var(--dimension-3);
}

@media (width <= 900px) {
  .board-settings__layout {
    flex-direction: column;
  }

  .board-settings__preview {
    display: none;
  }

  .board-settings__body {
    flex: 1 1 100%;
  }
}

.board-settings__footer-spacer {
  flex: 1;
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

.board-settings__template-preview {
  display: flex;
  align-items: baseline;
  gap: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-3);
  background: var(--bg-elevated, var(--bg-hover));
  border-radius: var(--dimension-2);
  font-size: 0.75rem;
}

.board-settings__template-preview-label {
  color: var(--text-muted);
}

.board-settings__template-preview code {
  color: var(--text);
  font-family: var(--font-family-mono, monospace);
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
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-4) 0;
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
}

/* Vertical stacks (former space-y utilities). Defined after __subsection /
   __type-section so the stack gap wins on elements carrying both classes,
   matching the old utility specificity. */
.board-settings__form > * + * {
  margin-top: 10px;
}

.board-settings__stack > * + * {
  margin-top: var(--dimension-4);
}

.board-settings__field > * + * {
  margin-top: var(--dimension-3);
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

.board-settings__num {
  width: 100px;
}

.board-settings__num--full {
  width: 100%;
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
  cursor: pointer;
}

.board-settings__errors {
  font-size: var(--font-size-normal);
  color: var(--color-light-red-40);
}

.board-settings__errors > * + * {
  margin-top: var(--dimension-2);
}

.board-settings__perm-cmk > * + * {
  margin-top: var(--dimension-6);
}

.board-settings__perm-cmk-intro {
  font-size: var(--font-size-large);
  color: var(--text);
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
