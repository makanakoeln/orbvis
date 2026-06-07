<template>
  <div class="settings-page">
    <div class="settings-page__body">
      <header class="settings-page__header">
        <CmkHeading type="h2">{{ heading }}</CmkHeading>
        <CmkParagraph v-if="subtitle" class="admin-subtitle">{{ subtitle }}</CmkParagraph>
      </header>

      <div v-if="loading" class="settings-page__loading">
        <CmkLoading />
      </div>

      <CmkAlertBox v-else-if="loadError" variant="error">{{ loadError }}</CmkAlertBox>

      <div v-else-if="schema" class="settings-page__layout">
        <nav class="settings-page__sidebar" aria-label="Settings sections">
          <button
            v-for="g in sidebarGroups"
            :key="g.key"
            type="button"
            class="settings-page__topic"
            :class="{ 'settings-page__topic--active': g.key === activeGroup }"
            @click="activeGroup = g.key"
          >
            <span class="settings-page__topic-title">{{ g.title }}</span>
            <span
              v-if="g.modified > 0"
              class="settings-page__topic-badge"
              :title="
                g.modified === 0
                  ? _t('no changes')
                  : _tn(
                      '1 field changed since last save',
                      '%{n} fields changed since last save',
                      g.modified,
                      { n: g.modified }
                    )
              "
            >
              {{ g.modified }}
            </span>
          </button>
        </nav>

        <div ref="detailEl" class="settings-page__detail" :data-active="activeGroup">
          <FormEdit v-model:data="data" :spec="schema" :backend-validation="validation" />
        </div>
      </div>
    </div>

    <Transition
      enter-from-class="settings-page__savebar--enter-from"
      enter-active-class="settings-page__savebar--enter-active"
      leave-to-class="settings-page__savebar--leave-to"
      leave-active-class="settings-page__savebar--leave-active"
    >
      <CmkAlertBox
        v-if="!loading && schema && saveBarState !== 'clean'"
        class="settings-page__savebar"
        :variant="saveBarVariant"
        size="small"
        :heading="saveBarHeading"
      >
        <div v-if="saveBarHasActions" class="settings-page__savebar-actions">
          <CmkButton variant="optional" :disabled="saving" @click="resetForm">
            {{ _t('Discard changes') }}
          </CmkButton>
          <CmkButton variant="primary" :disabled="saving" @click="handleSave">
            {{ saving ? _t('Saving…') : _t('Save') }}
          </CmkButton>
        </div>
      </CmkAlertBox>
    </Transition>

    <OrbUnsavedChangesDialog
      :open="leaveDialogOpen"
      @confirm="confirmLeave"
      @cancel="cancelLeave"
    />
  </div>
</template>

<script setup lang="ts">
import FormEdit from '@cmk/form/FormEdit.vue'
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, onMounted, onUnmounted, ref } from 'vue'

import OrbUnsavedChangesDialog from '@/components/OrbUnsavedChangesDialog.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkButton from '@/components/cmk/CmkButton'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkHeading from '@/components/cmk/typography/CmkHeading'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'

import { systemSettingsApi } from '@/api/client'
import { useDictionaryGroupAttrs } from '@/composables/useDictionaryGroupAttrs'
import { useFormSpecSchema } from '@/composables/useFormSpecSchema'
import { useSaveBarState } from '@/composables/useSaveBarState'
import { useUnsavedChangesGuard } from '@/composables/useUnsavedChangesGuard'
import { useAuthStore } from '@/stores/auth'
import usei18n from '@/vendor/cmk/lib/i18n'

type Validation = NonNullable<VueFormspecComponents['validation_message']>[]

interface SchemaElement {
  name: string
  group?: { key?: string | null; title?: string | null } | null
}
interface DictionarySchema {
  elements?: SchemaElement[]
  title?: string
  help?: string
}

// structuredClone fails on Vue's reactive proxies; settings payloads are
// pure JSON so a stringify round-trip is the safe equivalent.
function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

const { _t, _tn } = usei18n()
const auth = useAuthStore()

const {
  schema,
  error: schemaError,
  load: loadSchema
} = useFormSpecSchema('system-settings', () => systemSettingsApi.getSchema(auth.accessToken ?? ''))

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const saveError = ref('')
const savedOk = ref(false)
const data = ref<unknown>({})
const initialData = ref<unknown>({})
const validation = ref<Validation>([])
const activeGroup = ref<string>('')
const detailEl = ref<HTMLElement | null>(null)
useDictionaryGroupAttrs(detailEl, () => (schema.value as DictionarySchema | null)?.elements)

let savedOkTimer: ReturnType<typeof setTimeout> | null = null
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null

const dirty = computed(() => JSON.stringify(data.value) !== JSON.stringify(initialData.value))

const heading = computed(() => (schema.value as DictionarySchema | null)?.title ?? _t('System'))
const subtitle = computed(
  () =>
    (schema.value as DictionarySchema | null)?.help ||
    _t('Runtime and integration options. Applies across all boards.')
)

const sidebarGroups = computed<{ key: string; title: string; modified: number }[]>(() => {
  const dict = schema.value as DictionarySchema | null
  if (!dict?.elements) return []
  const cur = (data.value ?? {}) as Record<string, unknown>
  const orig = (initialData.value ?? {}) as Record<string, unknown>
  const acc = new Map<string, { title: string; modified: number }>()
  for (const el of dict.elements) {
    const key = el.group?.key ?? '-ungrouped-'
    const title = el.group?.title || key
    const entry = acc.get(key) ?? { title, modified: 0 }
    const here = el.name in cur
    const before = el.name in orig
    if (
      here !== before ||
      (here && JSON.stringify(cur[el.name]) !== JSON.stringify(orig[el.name]))
    ) {
      entry.modified += 1
    }
    acc.set(key, entry)
  }
  return Array.from(acc.entries()).map(([key, v]) => ({
    key,
    title: v.title,
    modified: v.modified
  }))
})

async function load() {
  const token = auth.accessToken
  if (!token) {
    loadError.value = 'Not authenticated'
    loading.value = false
    return
  }
  try {
    const [, values] = await Promise.all([loadSchema(), systemSettingsApi.getForm(token)])
    if (schemaError.value) {
      loadError.value = schemaError.value
      return
    }
    initialData.value = deepClone(values)
    data.value = deepClone(values)
    activeGroup.value = sidebarGroups.value[0]?.key ?? ''
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  data.value = deepClone(initialData.value)
  savedOk.value = false
  saveError.value = ''
}

async function handleSave() {
  const token = auth.accessToken
  if (!token) return
  saving.value = true
  saveError.value = ''
  savedOk.value = false
  try {
    const updated = await systemSettingsApi.updateForm(data.value as Record<string, unknown>, token)
    initialData.value = deepClone(updated)
    data.value = deepClone(updated)
    savedOk.value = true
    if (savedOkTimer) clearTimeout(savedOkTimer)
    savedOkTimer = setTimeout(() => {
      savedOk.value = false
    }, 3000)
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : _t('Save failed')
    if (saveErrorTimer) clearTimeout(saveErrorTimer)
    saveErrorTimer = setTimeout(() => {
      saveError.value = ''
    }, 5000)
  } finally {
    saving.value = false
  }
}

const { dialogOpen: leaveDialogOpen, confirmLeave, cancelLeave } = useUnsavedChangesGuard(dirty)

const {
  state: saveBarState,
  variant: saveBarVariant,
  hasActions: saveBarHasActions,
  heading: saveBarHeading
} = useSaveBarState({ dirty, saving, savedOk, error: saveError })

onMounted(load)

onUnmounted(() => {
  if (savedOkTimer) clearTimeout(savedOkTimer)
  if (saveErrorTimer) clearTimeout(saveErrorTimer)
})
</script>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.settings-page__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.settings-page__header {
  padding: var(--dimension-7) var(--dimension-8) var(--dimension-6);
}

.settings-page__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
}

.settings-page__savebar {
  margin: 0;
}

/* CmkAlertBox renders each variant's tint at 25-50 % alpha (mixed onto
   ``transparent``), which lets scrolled page content show through the sticky
   bar. Re-flatten every variant onto the page background so the hue stays
   visible while the bar becomes fully opaque. */
.settings-page__savebar.cmk-alert-box--warning {
  background-color: color-mix(in srgb, var(--color-yellow-50) 25%, var(--bg));
}

.settings-page__savebar.cmk-alert-box--error {
  background: color-mix(in srgb, var(--color-dark-red-50) 50%, var(--bg));
}

.settings-page__savebar.cmk-alert-box--success {
  background: color-mix(in srgb, var(--color-corporate-green-50) 25%, var(--bg));
}

.settings-page__savebar.cmk-alert-box--info,
.settings-page__savebar.cmk-alert-box--loading {
  background-color: color-mix(in srgb, var(--color-dark-blue-50) 25%, var(--bg));
}

.settings-page__savebar :deep(.cmk-alert-box__text) {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-5);
}

.settings-page__savebar :deep(.cmk-alert-box__body) {
  margin-left: auto;
}

.settings-page__savebar-actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.settings-page__savebar :deep(.cmk-button) {
  height: var(--dimension-9);
}

.settings-page__savebar--enter-from,
.settings-page__savebar--leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.settings-page__savebar--enter-active,
.settings-page__savebar--leave-active {
  transition:
    opacity 180ms ease-out,
    transform 180ms ease-out;
}

.settings-page__layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: var(--dimension-7);
  padding: 0 var(--dimension-8);
  flex: 1;
  align-items: start;
  min-height: 0;
}

.settings-page__sidebar {
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: sticky;
  top: 0;
  align-self: start;
}

.settings-page__topic {
  text-align: left;
  background: none;
  border: 0;
  border-left: 3px solid transparent;
  padding: var(--dimension-3) var(--dimension-5);
  font-size: 14px;

  /* CMK's theme-aware dimmed-text token. See GlobalSettingsView for
       the rationale — short version: ``--text-muted`` used to be
       near-white in light theme until the body bridge in style.css
       was wired to ``--font-color-dimmed``. */
  color: var(--font-color-dimmed, var(--text-muted));
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-3);
  transition:
    background-color 120ms,
    color 120ms,
    border-color 120ms;
}

.settings-page__topic-title {
  flex: 1;
  min-width: 0;
}

.settings-page__topic-badge {
  flex-shrink: 0;
  min-width: 20px;
  height: 18px;
  padding: 0 6px;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  text-align: center;
  background: var(--color-corporate-green-50);
  color: var(--bg-surface);
}

.settings-page__topic:hover {
  background: var(--bg-hover, rgb(127 127 127 / 8%));
  color: var(--font-color, var(--text));
}

.settings-page__topic--active {
  border-left-color: var(--color-corporate-green-50);
  background: rgb(21 209 160 / 12%);
  color: var(--font-color, var(--text));
  font-weight: 600;
}

/* Match by exact key — nested FormDictionary rows (CascadingSingleChoice
   branches etc.) use ``-ungrouped-N`` keys and would otherwise be hit by
   a generic ``tr[data-group]`` blanket. */
.settings-page__detail :deep(tr[data-group='server']),
.settings-page__detail :deep(tr[data-group='checkmk']),
.settings-page__detail :deep(tr[data-group='features']) {
  display: none !important;
}

.settings-page__detail[data-active='server'] :deep(tr[data-group='server']),
.settings-page__detail[data-active='checkmk'] :deep(tr[data-group='checkmk']),
.settings-page__detail[data-active='features'] :deep(tr[data-group='features']) {
  display: table-row !important;
}

/* Each sidebar entry maps 1:1 to a single group on this page — hide the
   inline group-title because the sidebar already names it. */
.settings-page__detail :deep(.form-dictionary__group-title) {
  display: none;
}

.settings-page__detail :deep(.form-help) {
  color: var(--text-muted);
  margin-bottom: var(--dimension-6);
}

/* Match Global Settings — add vertical breathing room between
   FormDictionary group rows without a border. */
.settings-page__detail :deep(tr[data-group] + tr[data-group] > td) {
  padding-top: var(--dimension-6);
}

.settings-page__detail[data-active='checkmk'] :deep(tr[data-group='checkmk'] > td),
.settings-page__detail[data-active='features'] :deep(tr[data-group='features'] > td) {
  padding-top: 0;
}
</style>
