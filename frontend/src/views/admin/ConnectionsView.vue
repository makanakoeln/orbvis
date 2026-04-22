<template>
  <div class="max-w-5xl">
    <div class="flex justify-between items-center" style="margin-bottom: 16px">
      <div>
        <h2 class="text-lg font-bold text-[var(--text)] tracking-tight">
          {{ t('admin.connectionsTitle') }}
        </h2>
        <p class="text-sm text-zinc-500" style="margin-top: 3px">
          {{ t('admin.connectionsSubtitle') }}
        </p>
      </div>
      <CmkButton variant="primary" @click="openCreate">
        <svg
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
          style="width: 13px; height: 13px; margin-right: 4px"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('admin.addConnection') }}
      </CmkButton>
    </div>

    <div v-if="store.loading" class="flex items-center justify-center py-8">
      <CmkLoading />
    </div>

    <CmkAlertBox v-else-if="store.error" variant="error">{{ store.error }}</CmkAlertBox>

    <div
      v-else-if="store.backends.length === 0"
      class="text-center py-16 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl"
    >
      <p class="text-zinc-500 text-sm">{{ t('admin.noConnections') }}</p>
      <p class="text-zinc-600 text-sm mt-1">{{ t('admin.noConnectionsHint') }}</p>
    </div>

    <div
      v-else
      class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
    >
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-[var(--border)]">
            <th
              class="text-left text-sm font-semibold text-zinc-500 tracking-wider"
              style="padding: 6px 12px"
            >
              {{ t('admin.status') }}
            </th>
            <th
              class="text-left text-sm font-semibold text-zinc-500 tracking-wider"
              style="padding: 6px 12px"
            >
              ID
            </th>
            <th
              class="text-left text-sm font-semibold text-zinc-500 tracking-wider"
              style="padding: 6px 12px"
            >
              {{ t('admin.displayLabel') }}
            </th>
            <th
              class="text-left text-sm font-semibold text-zinc-500 tracking-wider"
              style="padding: 6px 12px"
            >
              {{ t('admin.type') }}
            </th>
            <th
              class="text-left text-sm font-semibold text-zinc-500 tracking-wider"
              style="padding: 6px 12px"
            >
              {{ t('admin.connection') }}
            </th>
            <th
              class="text-right text-sm font-semibold text-zinc-500 tracking-wider"
              style="padding: 6px 12px"
            >
              {{ t('admin.actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--border)]">
          <tr
            v-for="b in store.backends"
            :key="b.id"
            class="hover:bg-[var(--bg-hover)] transition-colors"
          >
            <!-- Status -->
            <td style="padding: 6px 12px">
              <button
                :disabled="statusLoading[b.id]"
                class="flex items-center gap-[6px] group cursor-pointer"
                :title="t('common.test')"
                @click="testExisting(b.id)"
              >
                <span class="relative flex shrink-0">
                  <span
                    v-if="statusLoading[b.id]"
                    class="rounded-full bg-zinc-500 animate-pulse"
                    style="width: 8px; height: 8px"
                  />
                  <span
                    v-else-if="statuses[b.id] === undefined"
                    class="rounded-full bg-zinc-600"
                    style="width: 8px; height: 8px"
                  />
                  <span
                    v-else-if="statuses[b.id]"
                    class="rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)]"
                    style="width: 8px; height: 8px"
                  />
                  <span v-else class="rounded-full bg-red-400" style="width: 8px; height: 8px" />
                </span>
                <span class="text-sm text-zinc-400 group-hover:text-zinc-200 transition-colors">
                  {{
                    statusLoading[b.id]
                      ? t('common.testing')
                      : (statusMessages[b.id] ?? t('common.test'))
                  }}
                </span>
                <!-- Refresh icon — visible on hover to signal clickability -->
                <svg
                  class="text-zinc-600 group-hover:text-zinc-400 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                  style="width: 11px; height: 11px"
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
            <td class="font-mono text-sm text-zinc-400" style="padding: 6px 12px">{{ b.id }}</td>
            <td class="text-zinc-300" style="padding: 6px 12px">{{ b.label || '—' }}</td>
            <td style="padding: 6px 12px">
              <CmkBadge
                size="small"
                type="outline"
                :color="
                  b.type === 'livestatus' ? 'success' : b.type === 'icinga2' ? 'warning' : 'default'
                "
                >{{ b.type }}</CmkBadge
              >
            </td>
            <td class="text-zinc-400 font-mono text-sm" style="padding: 6px 12px">
              <template v-if="b.type === 'livestatus'">
                {{ b.socket_path || `${b.host}:${b.port}` }}
              </template>
              <template v-else-if="b.type === 'icinga2'">
                {{ b.icinga2_url || '—' }}
              </template>
              <span v-else class="text-zinc-700">{{ t('admin.builtIn') }}</span>
            </td>
            <td class="text-right" style="padding: 6px 12px">
              <div class="flex items-center justify-end gap-[4px]">
                <button
                  class="p-[4px] rounded-md text-zinc-600 hover:text-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-50)]/10 transition-all"
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
                  class="p-[4px] rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
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

    <ConfirmDialog
      v-if="deleteTarget"
      :title="t('admin.deleteConnection', { id: deleteTarget })"
      :message="t('board.cannotBeUndone')"
      :confirm-label="t('common.delete')"
      @confirm="confirmRemove"
      @cancel="deleteTarget = null"
    />

    <!-- Create / Edit dialog -->
    <Teleport to="body">
      <div v-if="dialog.open" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="dialog.open = false" />
        <div
          class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-xl w-[30rem] max-h-[90vh] overflow-y-auto"
          style="padding: 16px"
        >
          <div class="flex items-center justify-between" style="margin-bottom: 16px">
            <h3 class="text-base font-bold text-[var(--text)]">
              {{
                dialog.mode === 'create' ? t('admin.addConnectionTitle') : t('admin.editConnection')
              }}
            </h3>
            <button
              class="p-[5px] rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
              @click="dialog.open = false"
            >
              <svg
                style="width: 14px; height: 14px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form class="space-y-[12px]" @submit.prevent="save">
            <div v-if="dialog.mode === 'create'" class="space-y-[4px]">
              <label class="text-sm font-medium text-zinc-400">{{ t('admin.connectionId') }}</label>
              <CmkInput v-model="form.id" placeholder="cmk_heute" field-size="FILL" />
              <p class="text-sm text-zinc-600">{{ t('admin.connectionIdHint') }}</p>
            </div>

            <div class="space-y-[4px]">
              <label class="text-sm font-medium text-zinc-400">{{ t('admin.displayLabel') }}</label>
              <CmkInput v-model="form.label" placeholder="Checkmk heute" field-size="FILL" />
            </div>

            <div class="space-y-[4px]">
              <label class="text-sm font-medium text-zinc-400">{{ t('admin.type') }}</label>
              <AppSelect
                v-model="form.type"
                :options="[
                  { value: 'livestatus', label: t('admin.connectionTypeLivestatus') },
                  { value: 'icinga2', label: t('admin.connectionTypeIcinga2') },
                  { value: 'test', label: t('admin.connectionTypeTest') },
                ]"
              />
            </div>

            <template v-if="form.type === 'livestatus'">
              <!-- Unix socket -->
              <div class="space-y-[4px]">
                <label class="text-sm font-medium text-zinc-400">{{ t('admin.unixSocket') }}</label>
                <CmkInput
                  v-model="form.socket_path"
                  placeholder="/omd/sites/heute/tmp/run/live"
                  field-size="FILL"
                />
              </div>

              <!-- OR divider -->
              <div class="relative flex items-center gap-[8px]">
                <div class="flex-1 border-t border-[var(--border)]" />
                <span class="text-sm text-zinc-600 shrink-0">{{ t('admin.orTcp') }}</span>
                <div class="flex-1 border-t border-[var(--border)]" />
              </div>

              <!-- TCP Host + Port -->
              <div class="grid grid-cols-[1fr_7rem] gap-[8px]">
                <div class="space-y-[4px]">
                  <label class="text-sm font-medium text-zinc-400">{{ t('admin.tcpHost') }}</label>
                  <CmkInput v-model="form.host" placeholder="192.168.1.10" field-size="FILL" />
                </div>
                <div class="space-y-[4px]">
                  <label class="text-sm font-medium text-zinc-400">{{ t('admin.port') }}</label>
                  <NumberInput v-model="form.port" min="1" max="65535" class="w-full" />
                </div>
              </div>

              <!-- Checkmk URL + Automation + Timeout -->
              <div class="border-t border-[var(--border)] pt-[12px] space-y-[12px]">
                <div class="space-y-[4px]">
                  <label class="text-sm font-medium text-zinc-400">{{
                    t('admin.checkmkUrl')
                  }}</label>
                  <CmkInput
                    v-model="form.checkmk_url"
                    placeholder="http://localhost/heute"
                    field-size="FILL"
                  />
                  <p class="text-sm text-zinc-600">{{ t('admin.contextLinks') }}</p>
                </div>
                <template v-if="!isCmc">
                  <div class="grid grid-cols-2 gap-[8px]">
                    <div class="space-y-[4px]">
                      <label class="text-sm font-medium text-zinc-400">{{
                        t('admin.automationUser')
                      }}</label>
                      <CmkInput
                        v-model="form.automation_user"
                        placeholder="automation"
                        field-size="FILL"
                      />
                    </div>
                    <div class="space-y-[4px]">
                      <label class="text-sm font-medium text-zinc-400">{{
                        t('admin.automationSecret')
                      }}</label>
                      <CmkInput
                        v-model="form.automation_secret"
                        type="password"
                        placeholder="••••••••"
                        field-size="FILL"
                      />
                    </div>
                  </div>
                  <p class="text-sm text-zinc-600">{{ t('admin.automationHint') }}</p>
                </template>
                <p v-else class="text-sm text-zinc-500">{{ t('admin.automationHintCmc') }}</p>
                <div class="space-y-[4px]">
                  <label class="text-sm font-medium text-zinc-400">{{ t('admin.timeout') }}</label>
                  <NumberInput
                    v-model="form.timeout"
                    min="1"
                    max="120"
                    step="0.5"
                    class="w-[112px]"
                  />
                  <p class="text-sm text-zinc-600">seconds</p>
                </div>
              </div>
            </template>

            <template v-if="form.type === 'icinga2'">
              <div class="space-y-[4px]">
                <label class="text-sm font-medium text-zinc-400">{{ t('admin.icinga2Url') }}</label>
                <CmkInput
                  v-model="form.icinga2_url"
                  placeholder="https://localhost:5665"
                  field-size="FILL"
                />
              </div>

              <div class="grid grid-cols-2 gap-[8px]">
                <div class="space-y-[4px]">
                  <label class="text-sm font-medium text-zinc-400">{{
                    t('admin.icinga2Username')
                  }}</label>
                  <CmkInput v-model="form.icinga2_username" placeholder="root" field-size="FILL" />
                </div>
                <div class="space-y-[4px]">
                  <label class="text-sm font-medium text-zinc-400">{{
                    t('admin.icinga2Password')
                  }}</label>
                  <CmkInput v-model="form.icinga2_password" type="password" field-size="FILL" />
                </div>
              </div>

              <div class="flex items-center gap-[8px]">
                <CmkCheckbox
                  v-model="form.icinga2_verify_ssl"
                  :label="t('admin.icinga2VerifySsl')"
                />
              </div>

              <div class="space-y-[4px]">
                <label class="text-sm font-medium text-zinc-400">{{ t('admin.timeout') }}</label>
                <NumberInput
                  v-model="form.timeout"
                  min="1"
                  max="120"
                  step="0.5"
                  class="w-[112px]"
                />
                <p class="text-sm text-zinc-600">seconds</p>
              </div>
            </template>

            <!-- Test result -->
            <div
              v-if="dialogTest.ran"
              class="flex items-start gap-[8px] rounded-lg ring-1 text-sm"
              style="padding: 8px 12px"
              :class="
                dialogTest.ok
                  ? 'bg-green-500/8 ring-green-500/20 text-green-400'
                  : 'bg-red-500/8 ring-red-500/20 text-red-400'
              "
            >
              <span
                class="rounded-full shrink-0 mt-1"
                style="width: 6px; height: 6px"
                :class="dialogTest.ok ? 'bg-green-400' : 'bg-red-400'"
              />
              {{ dialogTest.message }}
            </div>

            <p v-if="formError" class="text-red-400 text-xs flex items-center gap-[4px]">
              <svg
                class="shrink-0"
                style="width: 12px; height: 12px"
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

            <div
              class="flex gap-[8px] justify-end border-t border-[var(--border)]"
              style="padding-top: 10px"
            >
              <CmkButton variant="secondary" @click="dialog.open = false">{{
                t('common.cancel')
              }}</CmkButton>
              <CmkButton variant="optional" :disabled="dialogTest.loading" @click="testDialog">
                {{ dialogTest.loading ? t('common.testing') : t('common.test') }}
              </CmkButton>
              <CmkButton variant="primary" :disabled="saving" @click="save">
                {{ saving ? t('common.saving') : t('common.save') }}
              </CmkButton>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkBadge from '@cmk/components/CmkBadge.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi } from '@/api/client';
import AppSelect from '@/components/AppSelect.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import NumberInput from '@/components/NumberInput.vue';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';
import { useConnectionsStore } from '@/stores/connections';
import type { BackendConfig } from '@/types/api';

const { t } = useI18n();
const store = useConnectionsStore();
const auth = useAuthStore();
const toast = useToast();

const statuses = reactive<Record<string, boolean>>({});
const statusMessages = reactive<Record<string, string>>({});
const statusLoading = reactive<Record<string, boolean>>({});

async function testExisting(id: string) {
  statusLoading[id] = true;
  try {
    const result = await connectionsApi.test(id, auth.accessToken!);
    statuses[id] = result.ok;
    statusMessages[id] = result.message;
  } catch (e: unknown) {
    statuses[id] = false;
    statusMessages[id] = e instanceof Error ? e.message : 'Error';
  } finally {
    statusLoading[id] = false;
  }
}

async function testAll() {
  for (const b of store.backends) testExisting(b.id);
}

const monitoringCore = ref<'cmc' | 'nagios' | null>(null);
const isCmc = computed(() => monitoringCore.value === 'cmc');

async function fetchContext(backendId: string) {
  monitoringCore.value = null;
  try {
    const ctx = await connectionsApi.context(backendId, auth.accessToken!);
    monitoringCore.value = ctx.monitoring_core;
  } catch {
    // fail safe: alle Felder anzeigen
  }
}

const deleteTarget = ref<string | null>(null);
const dialog = reactive({ open: false, mode: 'create' as 'create' | 'edit', editId: '' });
const saving = ref(false);
const formError = ref('');
const dialogTest = reactive({ loading: false, ran: false, ok: false, message: '' });

const emptyForm = (): BackendConfig => ({
  id: '',
  type: 'livestatus',
  label: '',
  socket_path: null,
  host: null,
  port: 6557,
  timeout: 10,
  checkmk_url: null,
  automation_user: null,
  automation_secret: null,
  icinga2_url: null,
  icinga2_username: null,
  icinga2_password: null,
  icinga2_verify_ssl: true,
});
const form = reactive<BackendConfig>(emptyForm());

function openCreate() {
  Object.assign(form, emptyForm());
  Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' });
  formError.value = '';
  dialog.mode = 'create';
  dialog.open = true;
  if (store.backends.length > 0) fetchContext(store.backends[0].id);
}

function openEdit(b: BackendConfig) {
  Object.assign(form, { ...b });
  Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' });
  formError.value = '';
  dialog.mode = 'edit';
  dialog.editId = b.id;
  dialog.open = true;
  fetchContext(b.id);
}

async function testDialog() {
  dialogTest.loading = true;
  dialogTest.ran = false;
  try {
    const result = await connectionsApi.testConnection({ ...form }, auth.accessToken!);
    dialogTest.ok = result.ok;
    dialogTest.message = result.message;
    dialogTest.ran = true;
  } catch (e: unknown) {
    dialogTest.ok = false;
    dialogTest.message = e instanceof Error ? e.message : 'Error';
    dialogTest.ran = true;
  } finally {
    dialogTest.loading = false;
  }
}

async function save() {
  formError.value = '';
  saving.value = true;
  try {
    if (dialog.mode === 'create') {
      await store.createBackend({ ...form });
      toast.success(t('admin.connectionCreated'));
    } else {
      const { id: _id, ...rest } = form;
      await store.updateBackend(dialog.editId, rest);
      toast.success(t('admin.connectionUpdated'));
    }
    dialog.open = false;
    testAll();
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : t('admin.saveFailed');
  } finally {
    saving.value = false;
  }
}

async function confirmRemove() {
  const id = deleteTarget.value;
  if (!id) return;
  deleteTarget.value = null;
  try {
    await store.deleteBackend(id);
    delete statuses[id];
    delete statusMessages[id];
    toast.success(t('admin.connectionDeleted'));
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : t('admin.deleteFailed'));
  }
}

onMounted(async () => {
  await store.fetchBackends();
  testAll();
});
</script>
