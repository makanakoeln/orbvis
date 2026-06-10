<template>
  <div class="orb-connfs">
    <div class="orb-connfs__header">
      <div>
        <CmkHeading type="h2">
          {{ _t('Monitoring Connections') }}
        </CmkHeading>
        <CmkParagraph class="admin-subtitle">
          {{ _t('Configure connections to monitoring systems') }}
        </CmkParagraph>
      </div>
      <CmkButton variant="primary" @click="openCreate">
        <CmkIcon name="add" size="small" style="margin-right: var(--dimension-3)" />
        {{ _t('Add Connection') }}
      </CmkButton>
    </div>

    <div v-if="store.loading" class="orb-connfs__loading">
      <CmkLoading />
    </div>

    <CmkAlertBox v-else-if="store.error" variant="error">{{ store.error }}</CmkAlertBox>

    <div v-else-if="store.connections.length === 0" class="orb-connfs__empty">
      <p class="orb-connfs__empty-text">{{ _t('No connections configured') }}</p>
      <p class="orb-connfs__empty-text orb-connfs__empty-text--hint">
        {{ _t('Add a connection to receive monitoring states') }}
      </p>
    </div>

    <div v-else class="orb-connfs__card">
      <table class="orb-connfs__table">
        <thead>
          <tr class="orb-connfs__head-row">
            <th class="orb-connfs__th">
              {{ _t('Status') }}
            </th>
            <th class="orb-connfs__th">ID</th>
            <th class="orb-connfs__th">
              {{ _t('Display label') }}
            </th>
            <th class="orb-connfs__th">
              {{ _t('Type') }}
            </th>
            <th class="orb-connfs__th">
              {{ _t('Connection') }}
            </th>
            <th class="orb-connfs__th orb-connfs__th--right">
              {{ _t('Actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="orb-connfs__body">
          <tr v-for="b in store.connections" :key="b.id" class="orb-connfs__row">
            <td class="orb-connfs__td">
              <button
                :disabled="statusLoading[b.id]"
                class="orb-connfs__status-btn"
                :title="_t('Test')"
                @click="testExisting(b.id)"
              >
                <span class="orb-connfs__dot-wrap">
                  <span
                    v-if="statusLoading[b.id]"
                    class="orb-connfs__dot orb-connfs__dot--loading"
                  />
                  <span
                    v-else-if="statuses[b.id] === undefined"
                    class="orb-connfs__dot orb-connfs__dot--pending"
                  />
                  <span v-else-if="statuses[b.id]" class="orb-connfs__dot orb-connfs__dot--ok" />
                  <span v-else class="orb-connfs__dot orb-connfs__dot--error" />
                </span>
                <span class="orb-connfs__status-label">
                  {{ statusLoading[b.id] ? _t('Testing…') : (statusMessages[b.id] ?? _t('Test')) }}
                </span>
                <svg
                  class="orb-connfs__refresh"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2.5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                  />
                </svg>
              </button>
            </td>
            <td class="orb-connfs__td orb-connfs__td--mono">
              {{ b.id }}
            </td>
            <td class="orb-connfs__td orb-connfs__td--text">
              {{ b.label || '—' }}
            </td>
            <td class="orb-connfs__td">
              <CmkBadge
                size="small"
                type="outline"
                :color="
                  b.type === 'livestatus' ? 'success' : b.type === 'icinga2' ? 'warning' : 'default'
                "
                >{{ b.type }}</CmkBadge
              >
            </td>
            <td class="orb-connfs__td orb-connfs__td--mono">
              <template v-if="b.type === 'livestatus'">
                {{ b.socket_path || (b.host ? (b.port ? `${b.host}:${b.port}` : b.host) : '—') }}
              </template>
              <template v-else-if="b.type === 'icinga2'">
                {{ b.icinga2_url || '—' }}
              </template>
              <span v-else>{{ _t('built-in') }}</span>
            </td>
            <td class="orb-connfs__td orb-connfs__td--right">
              <div class="orb-connfs__actions">
                <button
                  class="orb-connfs__action-btn orb-connfs__action-btn--edit"
                  :title="_t('Edit')"
                  @click="openEdit(b)"
                >
                  <CmkIcon name="edit" size="small" />
                </button>
                <button
                  class="orb-connfs__action-btn orb-connfs__action-btn--delete"
                  :title="_t('Delete')"
                  @click="deleteTarget = b.id"
                >
                  <CmkIcon name="delete" size="small" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <OrbConfirmDialog
      :open="!!deleteTarget"
      :title="deleteTarget ? _t('Delete connection &quot;%{id}&quot;?', { id: deleteTarget }) : ''"
      :message="_t('This cannot be undone.')"
      :confirm-label="_t('Delete')"
      @confirm="confirmRemove"
      @cancel="deleteTarget = null"
    />

    <CmkSlideInDialog
      v-if="dialog.open"
      :open="dialog.open"
      size="small"
      :header="{
        title: dialog.mode === 'create' ? _t('Add Connection') : _t('Edit Connection'),
        closeButton: true
      }"
      @close="closeDialog"
    >
      <div class="connection-edit__body">
        <div class="connection-edit__id">
          <CmkLabel>{{ _t('Connection ID') }}</CmkLabel>
          <CmkInput
            v-if="dialog.mode === 'create'"
            v-model="dialogId"
            placeholder="cmk_heute"
            field-size="FILL"
          />
          <p v-else class="connection-edit__id-readonly">{{ dialogId }}</p>
          <p v-if="dialog.mode === 'create'" class="connection-edit__hint">
            {{ _t('Letters, digits, hyphens and underscores only — used in URLs and configs') }}
          </p>
        </div>

        <div v-if="schemaError" class="connection-edit__schema-error">
          {{ schemaError }}
        </div>
        <div v-else-if="!formSchema" class="connection-edit__loading">
          <CmkLoading />
        </div>
        <FormEdit v-else v-model:data="formSpecData" :spec="formSchema" :backend-validation="[]" />

        <CmkAlertBox v-if="dialogTest.ran" :variant="dialogTest.ok ? 'success' : 'error'">
          {{ dialogTest.message }}
        </CmkAlertBox>

        <p v-if="formError" class="connection-edit__error">
          {{ formError }}
        </p>

        <div class="connection-edit__footer">
          <CmkButton variant="secondary" @click="closeDialog">
            {{ _t('Cancel') }}
          </CmkButton>
          <CmkButton
            variant="optional"
            :disabled="dialogTest.loading || !formSchema"
            @click="testDialog"
          >
            {{ dialogTest.loading ? _t('Testing…') : _t('Test') }}
          </CmkButton>
          <CmkButton variant="primary" :disabled="saving || !formSchema || !isDirty" @click="save">
            {{ saving ? _t('Saving…') : _t('Save') }}
          </CmkButton>
        </div>
      </div>
    </CmkSlideInDialog>
  </div>
</template>

<script setup lang="ts">
import FormEdit from '@cmk/form/FormEdit.vue'
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch'
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, onMounted, reactive, ref } from 'vue'

import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkBadge from '@/components/cmk/CmkBadge'
import CmkButton from '@/components/cmk/CmkButton'
import CmkIcon from '@/components/cmk/CmkIcon'
import CmkLabel from '@/components/cmk/CmkLabel'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkSlideInDialog from '@/components/cmk/CmkSlideInDialog'
import CmkHeading from '@/components/cmk/typography/CmkHeading'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { connectionsApi, connectionsApiFormSpec } from '@/api/client'
import { orbFormComponents } from '@/composables/orbFormComponents'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useConnectionsStore } from '@/stores/connections'
import type { ConnectionConfig } from '@/types/api'
import { asFormSpecSchema } from '@/utils/formSpec'
import usei18n from '@/vendor/cmk/lib/i18n'

type Schema = NonNullable<VueFormspecComponents['components']>

initializeComponentRegistry(orbFormComponents)

const { _t } = usei18n()
const store = useConnectionsStore()
const auth = useAuthStore()
const toast = useToast()

const statuses = reactive<Record<string, boolean>>({})
const statusMessages = reactive<Record<string, string>>({})
const statusLoading = reactive<Record<string, boolean>>({})

async function testExisting(id: string) {
  statusLoading[id] = true
  try {
    const result = await connectionsApi.test(id, auth.accessToken!)
    statuses[id] = result.ok
    statusMessages[id] = result.message
  } catch (e: unknown) {
    statuses[id] = false
    statusMessages[id] = e instanceof Error ? e.message : 'Error'
  } finally {
    statusLoading[id] = false
  }
}

async function testAll() {
  for (const b of store.connections) testExisting(b.id)
}

const deleteTarget = ref<string | null>(null)
const dialog = reactive({ open: false, mode: 'create' as 'create' | 'edit' })
const saving = ref(false)
const formError = ref('')
const schemaError = ref('')
const dialogId = ref('')
const dialogTest = reactive({ loading: false, ran: false, ok: false, message: '' })

const formSchema = ref<Schema | null>(null)
const formSpecData = ref<Record<string, unknown>>({})

// Snapshot the form state at open time so we can disable Save when nothing
// changed and confirm before discarding edits on cancel/close.
const initialSnapshot = ref('')
const isDirty = computed(
  () => JSON.stringify({ id: dialogId.value, data: formSpecData.value }) !== initialSnapshot.value
)

async function ensureSchema() {
  if (formSchema.value) return
  try {
    const spec = await connectionsApiFormSpec.getSchema(auth.accessToken!)
    formSchema.value = asFormSpecSchema(spec)
  } catch (e: unknown) {
    schemaError.value = e instanceof Error ? e.message : 'Schema load failed'
  }
}

function prepareDialog(mode: 'create' | 'edit', id: string) {
  Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' })
  formError.value = ''
  schemaError.value = ''
  dialog.mode = mode
  dialogId.value = id
  formSpecData.value = {}
  initialSnapshot.value = JSON.stringify({ id, data: {} })
  dialog.open = true
}

async function openCreate() {
  prepareDialog('create', '')
  await ensureSchema()
  // After schema arrives, seed defaults so the cascading 'type' starts on
  // livestatus instead of an empty body.
  if (formSchema.value) {
    const dv = (formSchema.value as { default_value?: unknown }).default_value
    if (dv && typeof dv === 'object') {
      formSpecData.value = structuredClone(dv) as Record<string, unknown>
    }
  }
  initialSnapshot.value = JSON.stringify({ id: dialogId.value, data: formSpecData.value })
}

async function openEdit(b: ConnectionConfig) {
  prepareDialog('edit', b.id)
  const fdataPromise = connectionsApiFormSpec.getFormData(b.id, auth.accessToken!)
  await ensureSchema()
  try {
    formSpecData.value = await fdataPromise
    initialSnapshot.value = JSON.stringify({ id: dialogId.value, data: formSpecData.value })
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : 'Failed to load connection data'
  }
}

function closeDialog() {
  if (isDirty.value && !window.confirm(_t('Discard your unsaved changes?'))) return
  dialog.open = false
}

function validateNewId(): string | null {
  if (dialog.mode !== 'create') return null
  const id = dialogId.value.trim()
  if (!id) return _t('Connection ID is required')
  if (!/^[A-Za-z0-9_-]+$/.test(id))
    return _t('Only letters, digits, hyphens (-) and underscores (_) allowed')
  if (store.connections.some((c) => c.id === id))
    return _t('A connection with this ID already exists')
  return null
}

async function testDialog() {
  formError.value = ''
  dialogTest.ran = false
  const idError = validateNewId()
  if (idError) {
    formError.value = idError
    return
  }
  dialogTest.loading = true
  try {
    const result = await connectionsApiFormSpec.testFromForm(
      dialogId.value.trim(),
      formSpecData.value,
      auth.accessToken!
    )
    dialogTest.ok = result.ok
    dialogTest.message = result.message
    dialogTest.ran = true
  } catch (e: unknown) {
    dialogTest.ok = false
    dialogTest.message = e instanceof Error ? e.message : 'Error'
    dialogTest.ran = true
  } finally {
    dialogTest.loading = false
  }
}

async function save() {
  formError.value = ''
  const idError = validateNewId()
  if (idError) {
    formError.value = idError
    return
  }
  saving.value = true
  try {
    const id = dialogId.value.trim()
    if (dialog.mode === 'create') {
      await connectionsApiFormSpec.createFromForm(id, formSpecData.value, auth.accessToken!)
      toast.success(_t('Connection created'))
    } else {
      await connectionsApiFormSpec.updateFromForm(id, formSpecData.value, auth.accessToken!)
      toast.success(_t('Connection updated'))
    }
    await store.fetchConnections()
    dialog.open = false
    testAll()
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : _t('Save failed')
  } finally {
    saving.value = false
  }
}

async function confirmRemove() {
  const id = deleteTarget.value
  if (!id) return
  deleteTarget.value = null
  try {
    await store.deleteConnection(id)
    delete statuses[id]
    delete statusMessages[id]
    toast.success(_t('Connection deleted'))
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : _t('Delete failed'))
  }
}

onMounted(async () => {
  await store.fetchConnections()
  testAll()
})
</script>

<style scoped>
.orb-connfs {
  max-width: 1024px;
}

.orb-connfs__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--dimension-6);
}

.orb-connfs__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.orb-connfs__empty {
  padding: 64px 0;
  text-align: center;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-connfs__empty-text {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-connfs__empty-text--hint {
  margin-top: var(--dimension-3);
}

.orb-connfs__card {
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-connfs__table {
  width: 100%;
  font-size: var(--font-size-large);
  line-height: 20px;
}

.orb-connfs__head-row {
  border-bottom: 1px solid var(--border);
}

.orb-connfs__th {
  padding: 6px 12px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-align: left;
  color: var(--text-muted);
}

.orb-connfs__th--right {
  text-align: right;
}

.orb-connfs__body > tr + tr {
  border-top: 1px solid var(--border);
}

.orb-connfs__row {
  transition: background-color 0.15s;
}

.orb-connfs__row:hover {
  background: var(--bg-hover);
}

.orb-connfs__td {
  padding: 6px 12px;
}

.orb-connfs__td--mono {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-connfs__td--text {
  color: var(--text);
}

.orb-connfs__td--right {
  text-align: right;
}

.orb-connfs__status-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.orb-connfs__dot-wrap {
  position: relative;
  display: flex;
  flex-shrink: 0;
}

.orb-connfs__dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.orb-connfs__dot--loading {
  background: var(--color-pending);
  animation: orb-connfs-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.orb-connfs__dot--pending {
  background: var(--color-pending);
}

.orb-connfs__dot--ok {
  background: var(--color-corporate-green-50);
  box-shadow: 0 0 6px color-mix(in srgb, var(--color-corporate-green-50) 60%, transparent);
}

.orb-connfs__dot--error {
  background: var(--color-light-red-40);
}

.orb-connfs__status-label {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  transition: color 0.15s;
}

.orb-connfs__status-btn:hover .orb-connfs__status-label {
  color: var(--text);
}

.orb-connfs__refresh {
  flex-shrink: 0;
  width: 11px;
  height: 11px;
  color: var(--text-muted);
  opacity: 0;
  transition: opacity 0.15s;
}

.orb-connfs__status-btn:hover .orb-connfs__refresh {
  opacity: 1;
}

.orb-connfs__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--dimension-3);
}

.orb-connfs__action-btn {
  padding: var(--dimension-3);
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.15s;
}

.orb-connfs__action-btn--edit:hover {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-connfs__action-btn--delete:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}

@keyframes orb-connfs-pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }
}

.connection-edit__body {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding-bottom: var(--dimension-5);
}

.connection-edit__id {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.connection-edit__id-readonly {
  font-family: var(--font-family-mono, monospace);
  font-size: 0.875rem;
  color: var(--text);
  padding: var(--dimension-3) var(--dimension-4);
  background: var(--bg-elevated, var(--bg-hover));
  border-radius: 6px;
  border: 1px solid var(--border);
  width: max-content;
}

.connection-edit__hint {
  margin-top: var(--dimension-2);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.connection-edit__schema-error {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}

.connection-edit__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-8) 0;
  color: var(--text-muted);
}

.connection-edit__error {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}

.connection-edit__footer {
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
  margin-top: var(--dimension-3);
}
</style>
