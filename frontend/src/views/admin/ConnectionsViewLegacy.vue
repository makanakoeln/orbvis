<template>
  <div class="orb-connlist">
    <div class="orb-connlist__header">
      <div>
        <CmkHeading type="h2">
          {{ t('admin.connectionsTitle') }}
        </CmkHeading>
        <CmkParagraph class="admin-subtitle">
          {{ t('admin.connectionsSubtitle') }}
        </CmkParagraph>
      </div>
      <CmkButton variant="primary" @click="openCreate">
        <svg
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
          style="width: 13px; height: 13px; margin-right: var(--dimension-3)"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('admin.addConnection') }}
      </CmkButton>
    </div>

    <div v-if="store.loading" class="orb-connlist__loading">
      <CmkLoading />
    </div>

    <CmkAlertBox v-else-if="store.error" variant="error">{{ store.error }}</CmkAlertBox>

    <div v-else-if="store.connections.length === 0" class="orb-connlist__empty">
      <p class="orb-connlist__empty-text">{{ t('admin.noConnections') }}</p>
      <p class="orb-connlist__empty-text orb-connlist__empty-text--hint">
        {{ t('admin.noConnectionsHint') }}
      </p>
    </div>

    <div v-else class="orb-connlist__card">
      <table class="orb-connlist__table">
        <thead>
          <tr class="orb-connlist__head-row">
            <th class="orb-connlist__th">
              {{ t('admin.status') }}
            </th>
            <th class="orb-connlist__th">ID</th>
            <th class="orb-connlist__th">
              {{ t('admin.displayLabel') }}
            </th>
            <th class="orb-connlist__th">
              {{ t('admin.type') }}
            </th>
            <th class="orb-connlist__th">
              {{ t('admin.connection') }}
            </th>
            <th class="orb-connlist__th orb-connlist__th--right">
              {{ t('admin.actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="orb-connlist__body">
          <tr v-for="b in store.connections" :key="b.id" class="orb-connlist__row">
            <!-- Status -->
            <td class="orb-connlist__td">
              <button
                :disabled="statusLoading[b.id]"
                class="orb-connlist__status-btn"
                :title="t('common.test')"
                @click="testExisting(b.id)"
              >
                <span class="orb-connlist__dot-wrap">
                  <span
                    v-if="statusLoading[b.id]"
                    class="orb-connlist__dot orb-connlist__dot--loading"
                  />
                  <span
                    v-else-if="statuses[b.id] === undefined"
                    class="orb-connlist__dot orb-connlist__dot--pending"
                  />
                  <span
                    v-else-if="statuses[b.id]"
                    class="orb-connlist__dot orb-connlist__dot--ok"
                  />
                  <span v-else class="orb-connlist__dot orb-connlist__dot--error" />
                </span>
                <span class="orb-connlist__status-label">
                  {{
                    statusLoading[b.id]
                      ? t('common.testing')
                      : (statusMessages[b.id] ?? t('common.test'))
                  }}
                </span>
                <!-- Refresh icon — visible on hover to signal clickability -->
                <svg
                  class="orb-connlist__refresh"
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
            <td class="orb-connlist__td orb-connlist__td--mono">
              {{ b.id }}
            </td>
            <td class="orb-connlist__td orb-connlist__td--text">
              {{ b.label || '—' }}
            </td>
            <td class="orb-connlist__td">
              <CmkBadge
                size="small"
                type="outline"
                :color="
                  b.type === 'livestatus' ? 'success' : b.type === 'icinga2' ? 'warning' : 'default'
                "
                >{{ b.type }}</CmkBadge
              >
            </td>
            <td class="orb-connlist__td orb-connlist__td--mono">
              <template v-if="b.type === 'livestatus'">
                {{ b.socket_path || (b.host ? (b.port ? `${b.host}:${b.port}` : b.host) : '—') }}
              </template>
              <template v-else-if="b.type === 'icinga2'">
                {{ b.icinga2_url || '—' }}
              </template>
              <span v-else>{{ t('admin.builtIn') }}</span>
            </td>
            <td class="orb-connlist__td orb-connlist__td--right">
              <div class="orb-connlist__actions">
                <button
                  class="orb-connlist__action-btn orb-connlist__action-btn--edit"
                  :title="t('common.edit')"
                  @click="openEdit(b)"
                >
                  <svg
                    style="width: 13px; height: 13px"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
                    />
                  </svg>
                </button>
                <button
                  class="orb-connlist__action-btn orb-connlist__action-btn--delete"
                  :title="t('common.delete')"
                  @click="deleteTarget = b.id"
                >
                  <svg
                    style="width: 13px; height: 13px"
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
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <OrbConfirmDialog
      :open="!!deleteTarget"
      :title="deleteTarget ? t('admin.deleteConnection', { id: deleteTarget }) : ''"
      :message="t('board.cannotBeUndone')"
      :confirm-label="t('common.delete')"
      @confirm="confirmRemove"
      @cancel="deleteTarget = null"
    />

    <OrbModal
      :open="dialog.open"
      :title="dialog.mode === 'create' ? t('admin.addConnectionTitle') : t('admin.editConnection')"
      closable
      @close="dialog.open = false"
    >
      <form class="connections-dialog__form" @submit.prevent="save">
        <div v-if="dialog.mode === 'create'" class="connections-dialog__field">
          <label class="connections-dialog__label">{{ t('admin.connectionId') }}</label>
          <CmkInput
            v-model="form.id"
            :placeholder="idPlaceholder"
            field-size="FILL"
            :external-errors="fieldErrors.id"
          />
          <p class="connections-dialog__hint">
            {{ t('admin.connectionIdHint') }}
          </p>
        </div>

        <div class="connections-dialog__field">
          <label class="connections-dialog__label">{{ t('admin.displayLabel') }}</label>
          <CmkInput v-model="form.label" :placeholder="labelPlaceholder" field-size="FILL" />
        </div>

        <div class="connections-dialog__field">
          <label class="connections-dialog__label">{{ t('admin.type') }}</label>
          <CmkDropdown
            :selected-option="form.type || null"
            :options="connectionTypeOptions"
            :width="'fill'"
            :label="t('admin.type')"
            @update:selected-option="form.type = ($event ?? '') as typeof form.type"
          />
        </div>

        <template v-if="form.type === 'livestatus'">
          <!-- Transport: socket vs TCP -->
          <div class="connections-dialog__field">
            <label class="connections-dialog__label">{{ t('admin.livestatusTransport') }}</label>
            <CmkDropdown
              :selected-option="livestatusMode"
              :options="livestatusModeOptions"
              :width="'fill'"
              :label="t('admin.livestatusTransport')"
              @update:selected-option="onLivestatusModeChange($event)"
            />
          </div>

          <!-- Unix socket -->
          <div v-if="livestatusMode === 'socket'" class="connections-dialog__field">
            <label class="connections-dialog__label">{{ t('admin.unixSocket') }}</label>
            <CmkInput
              v-model="form.socket_path"
              placeholder="/var/run/check_mk/live"
              field-size="FILL"
              :external-errors="fieldErrors.socket_path"
            />
          </div>

          <!-- TCP Host + Port -->
          <div v-else class="connections-dialog__row connections-dialog__row--host-port">
            <div class="connections-dialog__field">
              <label class="connections-dialog__label">{{ t('admin.tcpHost') }}</label>
              <CmkInput
                v-model="form.host"
                placeholder="monitoring.example.com"
                field-size="FILL"
                :external-errors="fieldErrors.host"
              />
            </div>
            <div class="connections-dialog__field">
              <label class="connections-dialog__label">{{ t('admin.port') }}</label>
              <NumberInput
                v-model="form.port"
                min="1"
                max="65535"
                class="connections-dialog__num-fill"
              />
            </div>
          </div>

          <!-- Checkmk URL + Automation + Timeout -->
          <div class="connections-dialog__section">
            <div class="connections-dialog__field">
              <label class="connections-dialog__label">{{ t('admin.checkmkUrl') }}</label>
              <CmkInput
                v-model="form.checkmk_url"
                placeholder="http://monitoring.example.com/mysite"
                field-size="FILL"
              />
              <p class="connections-dialog__hint">
                {{ t('admin.contextLinks') }}
              </p>
            </div>
            <template v-if="!isCmc">
              <div class="connections-dialog__row">
                <div class="connections-dialog__field">
                  <label class="connections-dialog__label">{{ t('admin.automationUser') }}</label>
                  <CmkInput
                    v-model="form.automation_user"
                    placeholder="automation"
                    field-size="FILL"
                  />
                </div>
                <div class="connections-dialog__field">
                  <label class="connections-dialog__label">{{ t('admin.automationSecret') }}</label>
                  <CmkInput
                    v-model="form.automation_secret"
                    type="password"
                    placeholder="••••••••"
                    field-size="FILL"
                  />
                </div>
              </div>
              <p class="connections-dialog__hint">
                {{ t('admin.automationHint') }}
              </p>
            </template>
            <p v-else class="connections-dialog__hint">
              {{ t('admin.automationHintCmc') }}
            </p>
            <div class="connections-dialog__field">
              <label class="connections-dialog__label">{{ t('admin.timeout') }}</label>
              <NumberInput
                v-model="form.timeout"
                min="1"
                max="120"
                step="0.5"
                class="connections-dialog__num"
              />
              <p class="connections-dialog__hint">seconds</p>
            </div>
          </div>
        </template>

        <template v-if="form.type === 'icinga2'">
          <div class="connections-dialog__field">
            <label class="connections-dialog__label">{{ t('admin.icinga2Url') }}</label>
            <CmkInput
              v-model="form.icinga2_url"
              placeholder="https://icinga.example.com:5665"
              field-size="FILL"
              :external-errors="fieldErrors.icinga2_url"
            />
          </div>

          <div class="connections-dialog__row">
            <div class="connections-dialog__field">
              <label class="connections-dialog__label">{{ t('admin.icinga2Username') }}</label>
              <CmkInput v-model="form.icinga2_username" placeholder="root" field-size="FILL" />
            </div>
            <div class="connections-dialog__field">
              <label class="connections-dialog__label">{{ t('admin.icinga2Password') }}</label>
              <CmkInput v-model="form.icinga2_password" type="password" field-size="FILL" />
            </div>
          </div>

          <div class="connections-dialog__checkbox-row">
            <CmkCheckbox v-model="form.icinga2_verify_ssl" :label="t('admin.icinga2VerifySsl')" />
          </div>

          <div class="connections-dialog__field">
            <label class="connections-dialog__label">{{ t('admin.timeout') }}</label>
            <NumberInput
              v-model="form.timeout"
              min="1"
              max="120"
              step="0.5"
              class="connections-dialog__num"
            />
            <p class="connections-dialog__hint">seconds</p>
          </div>
        </template>

        <!-- Test result -->
        <div
          v-if="dialogTest.ran"
          class="connections-dialog__test"
          :class="dialogTest.ok ? 'connections-dialog__test--ok' : 'connections-dialog__test--fail'"
        >
          <span
            class="connections-dialog__test-dot"
            :class="
              dialogTest.ok
                ? 'connections-dialog__test-dot--ok'
                : 'connections-dialog__test-dot--fail'
            "
          />
          {{ dialogTest.message }}
        </div>

        <p v-if="formError" class="connections-dialog__error">
          <svg
            class="connections-dialog__error-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z"
            />
          </svg>
          {{ formError }}
        </p>
      </form>
      <template #footer>
        <CmkButton variant="secondary" @click="dialog.open = false">
          {{ t('common.cancel') }}
        </CmkButton>
        <CmkButton variant="optional" :disabled="dialogTest.loading" @click="testDialog">
          {{ dialogTest.loading ? t('common.testing') : t('common.test') }}
        </CmkButton>
        <CmkButton
          variant="primary"
          :disabled="saving || !isFormValid"
          :title="!isFormValid ? saveBlockedTitle : ''"
          @click="save"
        >
          {{ saving ? t('common.saving') : t('common.save') }}
        </CmkButton>
      </template>
    </OrbModal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import NumberInput from '@/components/NumberInput.vue'
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import OrbModal from '@/components/OrbModal.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkBadge from '@/components/cmk/CmkBadge'
import CmkButton from '@/components/cmk/CmkButton'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkHeading from '@/components/cmk/typography/CmkHeading'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { ApiError, connectionsApi } from '@/api/client'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useConnectionsStore } from '@/stores/connections'
import type { ConnectionConfig } from '@/types/api'

const { t } = useI18n()
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

const monitoringCore = ref<'cmc' | 'nagios' | null>(null)
const isCmc = computed(() => monitoringCore.value === 'cmc')

async function fetchContext(connectionId: string) {
  monitoringCore.value = null
  try {
    const ctx = await connectionsApi.context(connectionId, auth.accessToken!)
    monitoringCore.value = ctx.monitoring_core
  } catch {
    // fail safe: alle Felder anzeigen
  }
}

const deleteTarget = ref<string | null>(null)
const dialog = reactive({ open: false, mode: 'create' as 'create' | 'edit', editId: '' })
const saving = ref(false)
const formError = ref('')
const dialogTest = reactive({ loading: false, ran: false, ok: false, message: '' })

// Clearing the other transport's fields on flip keeps "what you see saved" honest.
type LivestatusMode = 'socket' | 'tcp'
const livestatusMode = ref<LivestatusMode>('socket')
const livestatusModeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'socket', title: t('admin.livestatusTransportSocket') },
    { name: 'tcp', title: t('admin.livestatusTransportTcp') }
  ]
}))
function onLivestatusModeChange(next: string | null) {
  if (next !== 'socket' && next !== 'tcp') return
  livestatusMode.value = next
  if (next === 'socket') {
    form.host = null
    form.port = null
  } else {
    form.socket_path = null
  }
}

const idPlaceholder = computed(() => {
  if (form.type === 'icinga2') return 'icinga-prod'
  if (form.type === 'test') return 'demo'
  return 'cmk-prod'
})
const labelPlaceholder = computed(() => {
  if (form.type === 'icinga2') return 'Icinga 2 — production'
  if (form.type === 'test') return 'Demo data'
  return 'Checkmk production'
})

const fieldErrors = reactive<Record<string, string[]>>({})
function clearFieldErrors() {
  for (const k of Object.keys(fieldErrors)) delete fieldErrors[k]
}

const ID_PATTERN = /^[a-zA-Z0-9_-]+$/

const liveValidationErrors = computed<Record<string, string>>(() => {
  const errs: Record<string, string> = {}
  if (dialog.mode === 'create') {
    const id = (form.id || '').trim()
    if (!id) {
      errs.id = t('admin.fieldRequired')
    } else if (!ID_PATTERN.test(id)) {
      errs.id = t('admin.connectionIdInvalid')
    }
  }
  if (form.type === 'livestatus') {
    if (livestatusMode.value === 'socket') {
      if (!(form.socket_path || '').trim()) errs.socket_path = t('admin.fieldRequired')
    } else {
      if (!(form.host || '').trim()) errs.host = t('admin.fieldRequired')
    }
  } else if (form.type === 'icinga2') {
    if (!(form.icinga2_url || '').trim()) errs.icinga2_url = t('admin.fieldRequired')
  }
  return errs
})
const isFormValid = computed(() => Object.keys(liveValidationErrors.value).length === 0)
const saveBlockedTitle = computed(() => {
  const errs = liveValidationErrors.value
  const fields = Object.keys(errs)
  if (!fields.length) return ''
  return t('admin.saveBlocked') + ' ' + fields.map((f) => `${f}: ${errs[f]}`).join('; ')
})

// Optional ``ConnectionConfig`` fields are required (nullable) in the dialog
// form so v-model bindings never carry ``undefined`` into the CMK inputs.
type ConnectionForm = ConnectionConfig &
  Required<
    Pick<
      ConnectionConfig,
      | 'socket_path'
      | 'host'
      | 'port'
      | 'checkmk_url'
      | 'automation_user'
      | 'automation_secret'
      | 'icinga2_url'
      | 'icinga2_username'
      | 'icinga2_password'
      | 'icinga2_verify_ssl'
    >
  >

const emptyForm = (): ConnectionForm => ({
  id: '',
  type: 'livestatus',
  label: '',
  socket_path: null,
  host: null,
  port: null,
  timeout: 10,
  checkmk_url: null,
  automation_user: null,
  automation_secret: null,
  icinga2_url: null,
  icinga2_username: null,
  icinga2_password: null,
  icinga2_verify_ssl: true
})
const form = reactive<ConnectionForm>(emptyForm())

const connectionTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'livestatus', title: t('admin.connectionTypeLivestatus') },
    { name: 'icinga2', title: t('admin.connectionTypeIcinga2') },
    {
      name: 'test',
      title: t('admin.connectionTypeTest'),
      muted: true,
      divider: true
    }
  ]
}))

function openCreate() {
  Object.assign(form, emptyForm())
  Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' })
  formError.value = ''
  clearFieldErrors()
  livestatusMode.value = 'socket'
  dialog.mode = 'create'
  dialog.open = true
  const firstConnection = store.connections[0]
  if (firstConnection) fetchContext(firstConnection.id)
}

function openEdit(b: ConnectionConfig) {
  Object.assign(form, { ...b })
  Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' })
  formError.value = ''
  clearFieldErrors()
  livestatusMode.value = b.host ? 'tcp' : 'socket'
  dialog.mode = 'edit'
  dialog.editId = b.id
  dialog.open = true
  fetchContext(b.id)
}

// Cross-field model_validator errors carry `loc: ["body"]` only — those land
// in formError; per-field errors get their last loc segment as the field key.
function populateFieldErrors(detail: unknown): boolean {
  clearFieldErrors()
  if (!Array.isArray(detail)) return false
  let handled = false
  for (const it of detail as { loc?: unknown[]; msg?: string }[]) {
    const msg = (it?.msg ?? '').replace(/^Value error,\s*/, '')
    const loc = Array.isArray(it?.loc) ? it.loc.filter((p) => p !== 'body') : []
    if (loc.length === 0) {
      formError.value = msg
      handled = true
      continue
    }
    const field = String(loc[loc.length - 1])
    if (!fieldErrors[field]) fieldErrors[field] = []
    fieldErrors[field].push(msg)
    handled = true
  }
  return handled
}

async function testDialog() {
  dialogTest.loading = true
  dialogTest.ran = false
  try {
    const result = await connectionsApi.testConnection({ ...form }, auth.accessToken!)
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
  clearFieldErrors()
  if (!isFormValid.value) {
    for (const [field, msg] of Object.entries(liveValidationErrors.value)) {
      fieldErrors[field] = [msg]
    }
    return
  }
  saving.value = true
  try {
    if (dialog.mode === 'create') {
      await store.createConnection({ ...form })
      toast.success(t('admin.connectionCreated'))
    } else {
      const { id: _id, ...rest } = form
      await store.updateConnection(dialog.editId, rest)
      toast.success(t('admin.connectionUpdated'))
    }
    dialog.open = false
    testAll()
  } catch (e: unknown) {
    const handled =
      e instanceof ApiError &&
      populateFieldErrors(
        e.detail && typeof e.detail === 'object'
          ? (e.detail as { detail?: unknown }).detail
          : undefined
      )
    if (!handled) {
      formError.value = e instanceof Error ? e.message : t('admin.saveFailed')
    }
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
    toast.success(t('admin.connectionDeleted'))
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : t('admin.deleteFailed'))
  }
}

onMounted(async () => {
  await store.fetchConnections()
  testAll()
})
</script>

<style scoped>
.orb-connlist {
  max-width: 1024px;
}

.orb-connlist__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--dimension-6);
}

.orb-connlist__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.orb-connlist__empty {
  padding: 64px 0;
  text-align: center;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-connlist__empty-text {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-connlist__empty-text--hint {
  margin-top: var(--dimension-3);
}

.orb-connlist__card {
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-connlist__table {
  width: 100%;
  font-size: var(--font-size-large);
  line-height: 20px;
}

.orb-connlist__head-row {
  border-bottom: 1px solid var(--border);
}

.orb-connlist__th {
  padding: 6px 12px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-align: left;
  color: var(--text-muted);
}

.orb-connlist__th--right {
  text-align: right;
}

.orb-connlist__body > tr + tr {
  border-top: 1px solid var(--border);
}

.orb-connlist__row {
  transition: background-color 0.15s;
}

.orb-connlist__row:hover {
  background: var(--bg-hover);
}

.orb-connlist__td {
  padding: 6px 12px;
}

.orb-connlist__td--mono {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-connlist__td--text {
  color: var(--text);
}

.orb-connlist__td--right {
  text-align: right;
}

.orb-connlist__status-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.orb-connlist__dot-wrap {
  position: relative;
  display: flex;
  flex-shrink: 0;
}

.orb-connlist__dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.orb-connlist__dot--loading {
  background: var(--color-pending);
  animation: orb-connlist-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.orb-connlist__dot--pending {
  background: var(--color-pending);
}

.orb-connlist__dot--ok {
  background: var(--color-corporate-green-50);
  box-shadow: 0 0 6px color-mix(in srgb, var(--color-corporate-green-50) 60%, transparent);
}

.orb-connlist__dot--error {
  background: var(--color-light-red-40);
}

.orb-connlist__status-label {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  transition: color 0.15s;
}

.orb-connlist__status-btn:hover .orb-connlist__status-label {
  color: var(--text);
}

.orb-connlist__refresh {
  flex-shrink: 0;
  width: 11px;
  height: 11px;
  color: var(--text-muted);
  opacity: 0;
  transition: opacity 0.15s;
}

.orb-connlist__status-btn:hover .orb-connlist__refresh {
  opacity: 1;
}

.orb-connlist__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--dimension-3);
}

.orb-connlist__action-btn {
  padding: var(--dimension-3);
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.15s;
}

.orb-connlist__action-btn--edit:hover {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-connlist__action-btn--delete:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}

@keyframes orb-connlist-pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }
}

.connections-dialog__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  width: 30rem;
  max-width: 90vw;
}

.connections-dialog__field > * + * {
  margin-top: var(--dimension-3);
}

.connections-dialog__label {
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
  color: var(--text-muted);
}

.connections-dialog__hint {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.connections-dialog__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--dimension-4);
}

.connections-dialog__row--host-port {
  grid-template-columns: 1fr 7rem;
}

.connections-dialog__num {
  width: 112px;
}

.connections-dialog__num-fill {
  width: 100%;
}

.connections-dialog__section {
  padding-top: var(--dimension-5);
  border-top: 1px solid var(--border);
}

.connections-dialog__section > * + * {
  margin-top: var(--dimension-5);
}

.connections-dialog__checkbox-row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.connections-dialog__test {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-4) 12px;
  font-size: var(--font-size-large);
  line-height: 20px;
  border-radius: 8px;
}

.connections-dialog__test--ok {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 8%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
}

.connections-dialog__test--fail {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 8%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 20%, transparent);
}

.connections-dialog__test-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.connections-dialog__test-dot--ok {
  background: var(--color-corporate-green-50);
}

.connections-dialog__test-dot--fail {
  background: var(--color-light-red-40);
}

.connections-dialog__error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}

.connections-dialog__error-icon {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
}
</style>
