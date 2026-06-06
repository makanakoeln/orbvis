<!--
    Legacy / non-FormSpec System Settings form.

    Restored from the System section of the pre-FormSpec
    GlobalSettingsView at git rev ``034578c~1`` (the last commit before
    the FormSpec admin views landed). Saves through the flat pydantic
    ``GET/PUT /api/v1/settings/system`` endpoints — those stay registered
    regardless of cmk.rulesets.v1 availability.

    Hidden by the GlobalSettingsView wrapper when ``form_specs`` is true
    (built-in / MKP); served as the active view when Standalone reports
    ``form_specs: false``.
-->
<template>
  <div class="orb-sset">
    <div style="margin-bottom: var(--dimension-6)">
      <CmkHeading type="h2">
        {{ _t('System') }}
      </CmkHeading>
      <CmkParagraph class="admin-subtitle">
        {{ _t('Runtime and integration options. Applies across all boards.') }}
      </CmkParagraph>
    </div>

    <div v-if="store.loading" class="orb-sset__loading">
      <CmkLoading />
    </div>

    <div v-else>
      <div class="orb-sset__cards">
        <section class="orb-sset__card">
          <button
            class="orb-sset__card-toggle"
            @click="sectionOpen.checkmkIntegration = !sectionOpen.checkmkIntegration"
          >
            <h3 class="orb-sset__card-title">
              {{ _t('Checkmk Integration') }}
            </h3>
            <svg
              class="orb-sset__chevron"
              :class="{ 'orb-sset__chevron--open': sectionOpen.checkmkIntegration }"
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
          <CmkCollapsible :open="sectionOpen.checkmkIntegration">
            <div class="orb-sset__card-body">
              <p class="orb-sset__intro">
                {{
                  _t('Global Checkmk URL used as fallback for connections without their own URL')
                }}
              </p>
              <label class="orb-sset__label">
                <span class="orb-sset__field-label">
                  {{ _t('Checkmk URL') }}
                  <CmkHelpText
                    :help="
                      _t('Set automatically when OrbVis runs inside a Checkmk/OMD installation')
                    "
                  />
                </span>
                <CmkInput
                  v-model="checkmkUrl"
                  placeholder="https://checkmk.example.com/mysite"
                  field-size="FILL"
                />
              </label>
            </div>
          </CmkCollapsible>
        </section>

        <section class="orb-sset__card">
          <button class="orb-sset__card-toggle" @click="sectionOpen.logging = !sectionOpen.logging">
            <h3 class="orb-sset__card-title">
              {{ _t('Logging') }}
            </h3>
            <svg
              class="orb-sset__chevron"
              :class="{ 'orb-sset__chevron--open': sectionOpen.logging }"
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
          <CmkCollapsible :open="sectionOpen.logging">
            <div class="orb-sset__card-body">
              <label class="orb-sset__label">
                <span class="orb-sset__field-label">
                  {{ _t('Log level') }}
                  <CmkHelpText
                    :help="
                      _t('Threshold for backend logs. Applied immediately, no restart required.')
                    "
                  />
                </span>
                <CmkDropdown
                  class="orb-sset__select"
                  :selected-option="form.log_level ?? null"
                  :options="logLevelOptions"
                  label=""
                  @update:selected-option="
                    (v) => {
                      form.log_level = (v as LogLevel) || null
                    }
                  "
                />
              </label>
            </div>
          </CmkCollapsible>
        </section>

        <section class="orb-sset__card">
          <button
            class="orb-sset__card-toggle"
            @click="sectionOpen.features = !sectionOpen.features"
          >
            <h3 class="orb-sset__card-title">
              {{ _t('Features') }}
            </h3>
            <svg
              class="orb-sset__chevron"
              :class="{ 'orb-sset__chevron--open': sectionOpen.features }"
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
          <CmkCollapsible :open="sectionOpen.features">
            <div class="orb-sset__card-body">
              <CmkCheckbox v-model="enableFolderBoards" :label="_t('Enable Folder boards')" />
              <p class="orb-sset__feature-hint">
                {{
                  _t(
                    'Offer the SETUP folder-tree board type in the board-type picker. Existing folder boards keep rendering even while this is off.'
                  )
                }}
              </p>
              <CmkCheckbox
                v-model="enableGraphObjects"
                :label="_t('Enable Graph objects')"
                style="margin-top: 12px"
              />
              <p class="orb-sset__feature-hint">
                {{
                  _t(
                    'Offer the (experimental) graph object type in the add-object picker. Existing graph objects keep rendering even while this is off.'
                  )
                }}
              </p>
            </div>
          </CmkCollapsible>
        </section>
      </div>

      <p v-if="saveError" class="orb-sset__error">{{ saveError }}</p>

      <div class="orb-sset__footer">
        <Transition
          enter-from-class="orb-sset__saved-enter-from"
          enter-active-class="orb-sset__saved-enter-active"
          leave-to-class="orb-sset__saved-leave-to"
          leave-active-class="orb-sset__saved-leave-active"
        >
          <span v-if="savedOk" class="orb-sset__saved">
            <svg
              class="orb-sset__saved-icon"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
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

import CmkButton from '@/components/cmk/CmkButton'
import CmkCollapsible from '@/components/cmk/CmkCollapsible/CmkCollapsible'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkHelpText from '@/components/cmk/CmkHelpText'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkHeading from '@/components/cmk/typography/CmkHeading'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { useSettingsStore } from '@/stores/settings'
import type { LogLevel, SystemSettings } from '@/types/api'
import usei18n from '@cmk/lib/i18n'

const { _t } = usei18n()
const store = useSettingsStore()

// CmkInput's v-model is non-null string; SystemSettings.checkmk_url is
// ``string | null | undefined``. Bridge with a computed setter so empty
// input clears back to ``null`` on save.
const form = reactive<SystemSettings>({ ...store.system })
const checkmkUrl = computed({
  get: () => form.checkmk_url ?? '',
  set: (v: string) => {
    form.checkmk_url = v || null
  }
})

const saving = ref(false)
const saveError = ref('')
const savedOk = ref(false)
let savedOkTimer: ReturnType<typeof setTimeout> | null = null
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null

const sectionOpen = reactive({
  checkmkIntegration: true,
  logging: false,
  features: false
})

const enableFolderBoards = computed({
  get: () => form.enable_folder_boards ?? false,
  set: (v: boolean) => {
    form.enable_folder_boards = v
  }
})

const enableGraphObjects = computed({
  get: () => form.enable_graph_objects ?? true,
  set: (v: boolean) => {
    form.enable_graph_objects = v
  }
})

const logLevelOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'DEBUG', title: 'DEBUG' },
    { name: 'INFO', title: 'INFO' },
    { name: 'WARNING', title: 'WARNING' },
    { name: 'ERROR', title: 'ERROR' },
    { name: 'CRITICAL', title: 'CRITICAL' }
  ]
}))

const dirty = computed(() => JSON.stringify(form) !== JSON.stringify(store.system))

watch(
  () => store.system,
  (val) => Object.assign(form, val),
  { deep: true }
)

function resetForm() {
  Object.assign(form, store.system)
  savedOk.value = false
  saveError.value = ''
}

async function handleSave() {
  saving.value = true
  saveError.value = ''
  savedOk.value = false
  try {
    await store.saveSystem({ ...form })
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
  await store.load()
  Object.assign(form, store.system)
})
</script>

<style scoped>
.orb-sset {
  max-width: 672px;
}

.orb-sset__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.orb-sset__cards {
  margin-bottom: var(--dimension-6);
}

.orb-sset__cards > * + * {
  margin-top: var(--dimension-6);
}

.orb-sset__card {
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-sset__card-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 14px 16px;
  text-align: left;
}

.orb-sset__card-title {
  font-size: var(--font-size-xlarge);
  line-height: 24px;
  font-weight: 600;
  color: var(--text-muted);
}

.orb-sset__chevron {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  transition: transform 200ms;
}

.orb-sset__chevron--open {
  transform: rotate(180deg);
}

.orb-sset__card-body {
  padding: 0 16px 14px;
}

.orb-sset__intro {
  margin-bottom: 10px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-sset__label {
  display: block;
}

.orb-sset__field-label {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  margin-bottom: 3px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-sset :deep(.orb-sset__select) {
  width: 240px;
}

.orb-sset__feature-hint {
  margin-top: var(--dimension-3);
  margin-left: var(--dimension-8);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-sset__error {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}

.orb-sset__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--dimension-4);
}

.orb-sset__saved {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-corporate-green-50);
}

.orb-sset__saved-icon {
  width: 14px;
  height: 14px;
}

.orb-sset__saved-enter-from {
  opacity: 0;
  transform: translateX(8px);
}

.orb-sset__saved-enter-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-sset__saved-leave-to {
  opacity: 0;
}

.orb-sset__saved-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
