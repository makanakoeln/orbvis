<template>
  <OrbModal :open="true" :title="_t('Create Map')" closable @close="$emit('close')">
    <form class="create-map__form" @submit.prevent="submit">
      <div class="create-map__field">
        <label class="create-map__label">{{ _t('Map ID') }}</label>
        <CmkInput
          :model-value="form.name"
          placeholder="my-map"
          field-size="FILL"
          @update:model-value="(v) => onNameInput(String(v ?? ''))"
        />
        <p v-if="nameError" class="create-map__error">{{ nameError }}</p>
        <p v-else-if="nameWarning" class="create-map__warning">{{ nameWarning }}</p>
        <p v-else class="create-map__hint">
          {{
            _t(
              'Letters, digits, hyphens and underscores only — spaces become hyphens automatically'
            )
          }}
        </p>
      </div>
      <div class="create-map__field">
        <label class="create-map__label">{{ _t('Display name') }}</label>
        <CmkInput
          v-model="form.alias"
          placeholder="My Map"
          field-size="FILL"
          @update:model-value="onAliasInput"
        />
      </div>
      <div class="create-map__field">
        <label class="create-map__label">{{ _t('Connection') }}</label>
        <template v-if="connectionsStore.connections.length > 0">
          <CmkDropdown
            :selected-option="form.connection_id || null"
            :options="connectionOptions"
            :width="'fill'"
            :label="_t('Connection')"
            @update:selected-option="form.connection_id = $event ?? ''"
          />
        </template>
        <template v-else>
          <CmkAlertBox variant="warning" size="small">
            {{ _t('No connections configured yet — create one first.') }}
            <router-link
              :to="{ name: 'admin-connections' }"
              class="create-map__link"
              @click="$emit('close')"
            >
              {{ _t('Manage connections →') }}
            </router-link>
          </CmkAlertBox>
        </template>
      </div>
      <div class="create-map__field">
        <label class="create-map__label">{{ _t('Map type') }}</label>
        <div class="create-map__type-grid" role="radiogroup" :aria-label="_t('Map type')">
          <button
            v-for="opt in mapTypeCards"
            :key="opt.name"
            type="button"
            role="radio"
            :aria-checked="form.view_type === opt.name"
            class="create-map__type-card"
            :class="{
              'create-map__type-card--selected': form.view_type === opt.name
            }"
            @click="form.view_type = opt.name"
          >
            <span class="create-map__type-card-title">{{ opt.title }}</span>
            <span class="create-map__type-card-desc">{{ opt.desc }}</span>
          </button>
        </div>
      </div>
    </form>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton
        variant="primary"
        :disabled="!form.name || !!nameError || !form.connection_id"
        @click="submit"
      >
        {{ _t('Create') }}
      </CmkButton>
    </template>
  </OrbModal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import OrbModal from '@/components/OrbModal.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkButton from '@/components/cmk/CmkButton'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { ApiError } from '@/api/client'
import { useMapsStore } from '@/stores/maps'
import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import { mapTypeOptions } from '@/utils/dropdownOptions'
import { sanitizeMapName, sanitizeStrippedChars, slugToTitleCase } from '@/utils/naming'
import usei18n from '@cmk/lib/i18n'

const emit = defineEmits<{ close: []; created: [name: string] }>()

const { _t } = usei18n()
const mapsStore = useMapsStore()
const connectionsStore = useConnectionsStore()
const settingsStore = useSettingsStore()

const form = ref({ name: '', alias: '', connection_id: '', view_type: 'static' })
const aliasTouched = ref(false)
const nameTouched = ref(false)

const connectionOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: connectionsStore.connections.map((b) => ({ name: b.id, title: b.label || b.id }))
}))
const mapTypeCards = computed(() => {
  const descriptions: Record<string, string> = {
    static: _t('Free placement of objects on a canvas or background image'),
    worldmap: _t('Objects positioned on an interactive world map using geo-coordinates'),
    flow: _t('Dynamic tree of all hosts and their relationships'),
    radar: _t('Automatic display of all hosts/services matching a group filter'),
    foldertree: _t(
      'Live status tree along the Checkmk SETUP folder hierarchy, with worst-state roll-up'
    ),
    presentation: _t('Design-first slide for dashboards and status walls — direct manipulation')
  }
  return mapTypeOptions(
    _t,
    settingsStore.system.enable_folder_maps,
    settingsStore.system.enable_presentation_maps
  ).map((o) => ({ ...o, desc: descriptions[o.name] ?? '' }))
})

const _NAME_RE = /^[a-zA-Z0-9_-]+$/
const _MAX_NAME_LEN = 64
const nameError = ref('')
const nameWarning = ref('')

function onNameInput(raw: string) {
  nameTouched.value = true
  const stripped = sanitizeStrippedChars(raw)
  form.value.name = sanitizeMapName(raw)
  if (form.value.name.length > _MAX_NAME_LEN) {
    nameError.value = _t('Map ID is too long (max %{max} characters)', { max: _MAX_NAME_LEN })
  } else if (form.value.name && !_NAME_RE.test(form.value.name)) {
    nameError.value = _t('Only letters, digits, hyphens (-) and underscores (_) allowed')
  } else {
    nameError.value = ''
  }
  nameWarning.value = stripped
    ? _t('Some characters were removed (umlauts, punctuation, symbols are not allowed)')
    : ''
  if (!aliasTouched.value) {
    form.value.alias = slugToTitleCase(form.value.name)
  }
}

function onAliasInput() {
  aliasTouched.value = true
  if (!nameTouched.value) {
    form.value.name = sanitizeMapName(form.value.alias).toLowerCase()
    nameError.value =
      form.value.name && !_NAME_RE.test(form.value.name)
        ? _t('Only letters, digits, hyphens (-) and underscores (_) allowed')
        : ''
  }
}

function pickBackendId() {
  const ids = connectionsStore.connections.map((b) => b.id)
  const preferred = settingsStore.settings.default_backend_id
  return (preferred && ids.includes(preferred) ? preferred : ids[0]) ?? ''
}

onMounted(async () => {
  await Promise.all([connectionsStore.fetchConnections(), settingsStore.load()])
  form.value.connection_id = pickBackendId()
  form.value.view_type = settingsStore.settings.default_map_type || 'static'
})

async function submit() {
  nameError.value = ''
  try {
    await mapsStore.createMap(
      form.value.name,
      form.value.alias,
      form.value.connection_id,
      form.value.view_type,
      null,
      settingsStore.settings.default_render_mode ?? 'default'
    )
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 409) {
        nameError.value = _t('A map with this ID already exists')
      } else if (err.status === 422) {
        nameError.value =
          err.message || _t('Only letters, digits, hyphens (-) and underscores (_) allowed')
      } else {
        nameError.value = err.message || `HTTP ${err.status}`
      }
    }
    return
  }
  const created = form.value.name
  form.value = {
    name: '',
    alias: '',
    connection_id: pickBackendId(),
    view_type: settingsStore.settings.default_map_type || 'static'
  }
  emit('created', created)
}
</script>

<style scoped>
.create-map__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  min-width: 380px;
}

.create-map__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.create-map__label {
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--text-muted);
}

.create-map__error {
  font-size: var(--font-size-normal);
  color: var(--color-light-red-40);
}

.create-map__warning {
  font-size: var(--font-size-normal);
  color: var(--color-yellow-50);
}

.create-map__hint {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}

.create-map__link {
  display: block;
  margin-top: var(--dimension-3);
  color: var(--color-yellow-50);
  font-weight: 600;
  text-decoration: underline;
}

.create-map__type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--dimension-3);
}

.create-map__type-card {
  text-align: left;
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition:
    border-color 120ms,
    background-color 120ms;
}

.create-map__type-card:hover {
  border-color: var(--color-corporate-green-50);
}

.create-map__type-card--selected {
  border-color: var(--color-corporate-green-50);
  background: color-mix(
    in srgb,
    var(--color-corporate-green-50) 10%,
    var(--default-form-element-bg-color)
  );
}

/* With an odd number of map types (currently 5) the last card would sit alone
   in a half-row; let it span the full width so the grid reads balanced. */
.create-map__type-card:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

.create-map__type-card-title {
  font-size: var(--font-size-normal);
  font-weight: 600;
  color: var(--text);
}

.create-map__type-card-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.35;
}
</style>
