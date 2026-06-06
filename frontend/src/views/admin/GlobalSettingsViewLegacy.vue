<template>
  <div class="orb-gset">
    <div style="margin-bottom: var(--dimension-6)">
      <CmkHeading type="h2">
        {{ _t('Global Settings') }}
      </CmkHeading>
      <CmkParagraph class="admin-subtitle">
        {{ _t('Default values applied when creating new boards and objects') }}
      </CmkParagraph>
    </div>

    <div v-if="store.loading" class="orb-gset__loading">
      <CmkLoading />
    </div>

    <div v-else>
      <!-- Group: Defaults applied when creating a new board -->
      <h3 class="orb-group-heading">{{ _t('When creating a new board') }}</h3>
      <div class="orb-gset__cards">
        <!-- New board defaults -->
        <section class="orb-gset__card">
          <button
            class="orb-gset__card-toggle"
            @click="sectionOpen.newBoardDefaults = !sectionOpen.newBoardDefaults"
          >
            <h3 class="orb-gset__card-title">
              {{ _t('New board defaults') }}
            </h3>
            <svg
              class="orb-gset__chevron"
              :class="{ 'orb-gset__chevron--open': sectionOpen.newBoardDefaults }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
              />
            </svg>
          </button>
          <CmkCollapsible :open="sectionOpen.newBoardDefaults">
            <div class="orb-gset__card-body orb-gset__field-row">
              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('Connection') }}</span>
                <CmkDropdown
                  class="orb-gset__select orb-gset__select--wide"
                  :selected-option="form.default_backend_id || null"
                  :options="connectionOptions"
                  label=""
                  @update:selected-option="form.default_backend_id = $event ?? ''"
                />
              </label>

              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('Board type') }}</span>
                <CmkDropdown
                  class="orb-gset__select"
                  :selected-option="form.default_map_type || null"
                  :options="mapTypeOptions"
                  label=""
                  @update:selected-option="form.default_map_type = $event ?? ''"
                />
              </label>
            </div>
          </CmkCollapsible>
        </section>
      </div>

      <!-- Group: Defaults applied to objects rendered on a board -->
      <h3 class="orb-group-heading">{{ _t('When rendering objects on a board') }}</h3>
      <div class="orb-gset__cards">
        <!-- Icon defaults -->
        <section class="orb-gset__card">
          <button
            class="orb-gset__card-toggle"
            @click="sectionOpen.iconDefaults = !sectionOpen.iconDefaults"
          >
            <h3 class="orb-gset__card-title">
              {{ _t('Icon defaults') }}
            </h3>
            <svg
              class="orb-gset__chevron"
              :class="{ 'orb-gset__chevron--open': sectionOpen.iconDefaults }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
              />
            </svg>
          </button>
          <CmkCollapsible :open="sectionOpen.iconDefaults">
            <div class="orb-gset__card-body orb-gset__field-row">
              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('Icon size') }}</span>
                <NumberInput v-model="form.icon_size" min="8" max="256" class="orb-gset__num" />
              </label>

              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('View type') }}</span>
                <CmkToggleButtonGroup
                  v-model="form.view_type"
                  :options="[
                    { value: 'icon', label: _t('Icon') },
                    { value: 'text', label: _t('Text only') },
                    {
                      value: 'gadget',
                      label: _t('Gadget')
                    }
                  ]"
                />
              </label>

              <label class="orb-gset__label">
                <span class="orb-gset__field-label orb-gset__field-label--help">
                  {{ _t('Z') }}
                  <CmkHelpText :help="_t('Stacking order – higher = in front')" />
                </span>
                <NumberInput v-model="form.z" min="1" max="999" class="orb-gset__num" />
              </label>
            </div>
          </CmkCollapsible>
        </section>

        <!-- Line defaults -->
        <section class="orb-gset__card">
          <button
            class="orb-gset__card-toggle"
            @click="sectionOpen.lineDefaults = !sectionOpen.lineDefaults"
          >
            <h3 class="orb-gset__card-title">
              {{ _t('Line defaults') }}
            </h3>
            <svg
              class="orb-gset__chevron"
              :class="{ 'orb-gset__chevron--open': sectionOpen.lineDefaults }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
              />
            </svg>
          </button>
          <CmkCollapsible :open="sectionOpen.lineDefaults">
            <div class="orb-gset__card-body orb-gset__field-row">
              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('Style') }}</span>
                <CmkDropdown
                  class="orb-gset__select"
                  :selected-option="form.line_style ?? null"
                  :options="lineStyleOpts"
                  label=""
                  @update:selected-option="
                    (v) => {
                      form.line_style = (v as LineStyle) || null
                    }
                  "
                />
              </label>

              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('Target') }}</span>
                <CmkToggleButtonGroup
                  v-model="form.url_target"
                  :options="[
                    { value: '_blank', label: _t('New tab') },
                    { value: '_self', label: _t('Same tab') },
                    { value: '_top', label: _t('Top frame') }
                  ]"
                />
              </label>
            </div>
          </CmkCollapsible>
        </section>

        <!-- Label defaults — Show-label is a master toggle in the card header.
                 Header uses a div+role=button instead of a native <button> so we can
                 nest the CmkSwitch <label> (invalid HTML inside <button>). -->
        <section class="orb-gset__card">
          <div
            class="orb-gset__card-toggle orb-gset__card-toggle--clickable"
            role="button"
            tabindex="0"
            @click="sectionOpen.labelDefaults = !sectionOpen.labelDefaults"
            @keydown.enter.prevent="sectionOpen.labelDefaults = !sectionOpen.labelDefaults"
            @keydown.space.prevent="sectionOpen.labelDefaults = !sectionOpen.labelDefaults"
          >
            <h3 class="orb-gset__card-title">
              {{ _t('Label defaults') }}
            </h3>
            <div class="orb-gset__card-actions" @click.stop>
              <label class="orb-gset__switch-label">
                <CmkSwitch v-model:data="form.label_show" />
                <span>{{ _t('Show label') }}</span>
              </label>
              <svg
                class="orb-gset__chevron orb-gset__chevron--pointer"
                :class="{ 'orb-gset__chevron--open': sectionOpen.labelDefaults }"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
                @click="sectionOpen.labelDefaults = !sectionOpen.labelDefaults"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
              </svg>
            </div>
          </div>
          <CmkCollapsible :open="sectionOpen.labelDefaults">
            <div class="orb-gset__card-body">
              <div
                class="orb-gset__label-fields"
                :class="{ 'orb-gset__label-fields--off': !form.label_show }"
              >
                <div class="label-subsection">
                  <p class="orb-section-title">
                    {{ _t('Appearance') }}
                  </p>
                  <div class="orb-gset__field-row">
                    <label class="orb-gset__label">
                      <span class="orb-gset__field-label">{{ _t('Size') }} (px)</span>
                      <NumberInput
                        v-model="form.label_size"
                        min="6"
                        max="72"
                        class="orb-gset__num"
                      />
                    </label>

                    <label class="orb-gset__label">
                      <span class="orb-gset__field-label">{{ _t('Color') }}</span>
                      <ColorInput v-model="form.label_color" default-color="#ffffff" />
                    </label>
                  </div>
                </div>

                <div class="label-subsection">
                  <p class="orb-section-title">
                    {{ _t('Background') }}
                  </p>
                  <ColorInput
                    v-model="form.label_background"
                    :enable-label="_t('Use background color')"
                    none-value="transparent"
                    default-color="#000000"
                  />
                </div>
              </div>
            </div>
          </CmkCollapsible>
        </section>

        <!-- Templates -->
        <section class="orb-gset__card">
          <button
            class="orb-gset__card-toggle"
            @click="sectionOpen.templates = !sectionOpen.templates"
          >
            <h3 class="orb-gset__card-title">
              {{ _t('Templates') }}
            </h3>
            <svg
              class="orb-gset__chevron"
              :class="{ 'orb-gset__chevron--open': sectionOpen.templates }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
              />
            </svg>
          </button>
          <CmkCollapsible :open="sectionOpen.templates">
            <div class="orb-gset__card-body orb-gset__template-stack">
              <p class="orb-gset__hint">
                {{
                  _t(
                    'Global fallback — applies to any board or object without its own template set'
                  )
                }}
              </p>
              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('Hover template') }}</span>
                <CmkInput
                  v-model="form.hover_template"
                  :placeholder="_t('e.g. {{name}} is {{state}}')"
                  field-size="FILL"
                />
              </label>

              <label class="orb-gset__label">
                <span class="orb-gset__field-label">{{ _t('Context template') }}</span>
                <CmkInput
                  v-model="form.context_template"
                  :placeholder="_t('e.g. {{name}} is {{state}}')"
                  field-size="FILL"
                />
              </label>
            </div>
          </CmkCollapsible>
        </section>
      </div>

      <p v-if="saveError" class="orb-gset__error">{{ saveError }}</p>

      <div class="orb-gset__footer">
        <Transition
          enter-from-class="orb-gset__saved-enter-from"
          enter-active-class="orb-gset__saved-enter-active"
          leave-to-class="orb-gset__saved-leave-to"
          leave-active-class="orb-gset__saved-leave-active"
        >
          <span v-if="savedOk" class="orb-gset__saved">
            <svg
              class="orb-gset__saved-icon"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2.5"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            {{ _t('Saved') }}
          </span>
        </Transition>
        <CmkButton variant="secondary" :disabled="!dirty" @click="resetForm">{{
          _t('Cancel')
        }}</CmkButton>
        <CmkButton variant="primary" :disabled="saving || !dirty" @click="handleSave">
          {{ saving ? _t('Saving…') : _t('Save') }}
        </CmkButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import ColorInput from '@/components/ColorInput.vue'
import NumberInput from '@/components/NumberInput.vue'
import CmkButton from '@/components/cmk/CmkButton'
import CmkCollapsible from '@/components/cmk/CmkCollapsible/CmkCollapsible'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkHelpText from '@/components/cmk/CmkHelpText'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkSwitch from '@/components/cmk/CmkSwitch'
import CmkToggleButtonGroup from '@/components/cmk/CmkToggleButtonGroup'
import CmkHeading from '@/components/cmk/typography/CmkHeading'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import type { GlobalSettings, LineStyle } from '@/types/api'
import { boardTypeOptions, lineStyleOptions } from '@/utils/dropdownOptions'
import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()
const store = useSettingsStore()
const connectionsStore = useConnectionsStore()

// Template fields are required (nullable) in the form so the v-model bindings
// never carry ``undefined`` into the CMK inputs.
type SettingsForm = GlobalSettings &
  Required<Pick<GlobalSettings, 'hover_template' | 'context_template'>>

const form = reactive<SettingsForm>({
  ...store.settings,
  hover_template: store.settings.hover_template ?? null,
  context_template: store.settings.context_template ?? null
})
const saving = ref(false)
const saveError = ref('')
const savedOk = ref(false)
let savedOkTimer: ReturnType<typeof setTimeout> | null = null
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null

// Open the first section by default — operators arriving on the page see
// what's configurable instead of an opaque list of collapsed headers.
const sectionOpen = reactive({
  iconDefaults: true,
  lineDefaults: false,
  labelDefaults: false,
  newBoardDefaults: false,
  templates: false
})

const connectionOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: connectionsStore.connections.length
    ? connectionsStore.connections.map((b) => ({ name: b.id, title: b.label || b.id }))
    : [{ name: 'live_1', title: 'live_1' }]
}))
const mapTypeOptions = computed(() => ({
  type: 'fixed' as const,
  // Offer folder-tree as a default board type only when the feature flag is on,
  // or when it is already the configured default (so it isn't silently dropped).
  suggestions: boardTypeOptions(
    _t,
    store.system.enable_folder_boards || form.default_map_type === 'foldertree'
  )
}))
const lineStyleOpts = computed(() => ({
  type: 'fixed' as const,
  suggestions: lineStyleOptions(_t)
}))
const dirty = computed(() => JSON.stringify(form) !== JSON.stringify(store.settings))

// Sync form when store finishes loading
watch(
  () => store.settings,
  (val) => Object.assign(form, val),
  { deep: true }
)

function resetForm() {
  Object.assign(form, store.settings)
  savedOk.value = false
  saveError.value = ''
}

async function handleSave() {
  saving.value = true
  saveError.value = ''
  savedOk.value = false
  try {
    await store.save({ ...form })
    savedOk.value = true
    if (savedOkTimer) clearTimeout(savedOkTimer)
    savedOkTimer = setTimeout(() => {
      savedOk.value = false
    }, 3000)
  } catch {
    saveError.value = _t('Save failed')
    if (saveErrorTimer) clearTimeout(saveErrorTimer)
    saveErrorTimer = setTimeout(() => {
      saveError.value = ''
    }, 5000)
  } finally {
    saving.value = false
  }
}

onUnmounted(() => {
  if (savedOkTimer) clearTimeout(savedOkTimer)
  if (saveErrorTimer) clearTimeout(saveErrorTimer)
})

onMounted(async () => {
  await Promise.all([store.load(), connectionsStore.fetchConnections()])
  Object.assign(form, store.settings)
})
</script>

<style scoped>
.orb-gset {
  max-width: 672px;
}

.orb-gset__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.orb-gset__cards {
  margin-bottom: var(--dimension-6);
}

.orb-gset__cards > * + * {
  margin-top: var(--dimension-6);
}

.orb-gset__card {
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-gset__card-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 14px 16px;
  text-align: left;
}

.orb-gset__card-toggle--clickable {
  cursor: pointer;
}

.orb-gset__card-title {
  font-size: var(--font-size-xlarge);
  line-height: 24px;
  font-weight: 600;
  color: var(--text-muted);
}

.orb-gset__card-actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
}

.orb-gset__chevron {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  transition: transform 200ms;
}

.orb-gset__chevron--pointer {
  cursor: pointer;
}

.orb-gset__chevron--open {
  transform: rotate(180deg);
}

.orb-gset__card-body {
  padding: 0 16px 14px;
}

.orb-gset__field-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--dimension-4) var(--dimension-5);
}

.orb-gset__label {
  display: block;
}

.orb-gset__field-label {
  display: block;
  margin-bottom: 3px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-gset__field-label--help {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
}

.orb-gset__switch-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  cursor: pointer;
}

.orb-gset :deep(.orb-gset__select) {
  width: 176px;
}

.orb-gset :deep(.orb-gset__select--wide) {
  width: 192px;
}

.orb-gset :deep(.orb-gset__num) {
  width: 80px;
}

.orb-gset__label-fields {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-gset__label-fields > * + * {
  margin-top: var(--dimension-6);
}

.orb-gset__label-fields--off {
  opacity: 0.4;
  pointer-events: none;
}

.orb-gset__template-stack > * + * {
  margin-top: 10px;
}

.orb-gset__hint {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-gset__error {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}

.orb-gset__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--dimension-4);
}

.orb-gset__saved {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-corporate-green-50);
}

.orb-gset__saved-icon {
  width: 14px;
  height: 14px;
}

.orb-gset__saved-enter-from {
  opacity: 0;
  transform: translateX(8px);
}

.orb-gset__saved-enter-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-gset__saved-leave-to {
  opacity: 0;
}

.orb-gset__saved-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.label-subsection {
  padding-top: var(--dimension-4);
  border-top: 1px solid var(--border);
}

.label-subsection:first-child {
  padding-top: 0;
  border-top: 0;
}
</style>
