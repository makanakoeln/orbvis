<template>
  <div class="max-w-3xl">
    <div class="flex justify-between items-center" style="margin-bottom: 16px">
      <div>
        <h2 class="text-base font-bold text-[var(--text)] tracking-tight">
          {{ t('admin.rolesAndPermissions') }}
        </h2>
        <p class="text-sm text-zinc-500" style="margin-top: 3px">{{ t('admin.rolesSubtitle') }}</p>
      </div>
      <CmkButton variant="primary" @click="showCreate = true">
        <svg
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
          style="width: 13px; height: 13px; margin-right: 4px"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('admin.newRole') }}
      </CmkButton>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-8">
      <CmkLoading />
    </div>

    <div v-else class="space-y-[8px]">
      <div
        v-for="role in roles"
        :key="role.role_id"
        class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl hover:ring-[var(--border)] transition-all"
        style="padding: 12px"
      >
        <div class="flex justify-between items-start gap-[12px]">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-[6px]" style="margin-bottom: 3px">
              <span class="font-semibold text-[var(--text)]">{{ role.name }}</span>
              <span
                class="text-xs rounded bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] text-zinc-500"
                style="padding: 1px 5px"
              >
                {{ role.permissions.length }} {{ t('admin.permissions') }}
              </span>
            </div>
            <div
              v-if="role.permissions.length"
              class="flex flex-wrap gap-[4px]"
              style="margin-top: 8px"
            >
              <span
                v-for="perm in role.permissions"
                :key="perm.perm_id"
                class="text-xs bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-md text-zinc-400 font-mono"
                style="padding: 1px 5px"
                >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span
              >
            </div>
            <p v-else class="text-xs text-zinc-600" style="margin-top: 6px">
              {{ t('admin.noPermissions') }}
            </p>
          </div>
          <div class="flex items-center gap-[3px] shrink-0">
            <button
              class="p-[4px] rounded-md text-zinc-600 hover:text-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-50)]/10 transition-all"
              :title="t('common.edit')"
              @click="openEdit(role)"
            >
              <svg
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
                style="width: 13px; height: 13px"
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
              @click="deleteTargetId = role.role_id"
            >
              <svg
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
                style="width: 13px; height: 13px"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-if="!roles.length" class="text-center py-[32px] text-zinc-600 text-sm">
        {{ t('admin.noRoles') }}
      </div>
    </div>

    <!-- Create role dialog -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreate = false" />
        <div
          class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-xl w-80"
          style="padding: 16px"
        >
          <div class="flex items-center justify-between" style="margin-bottom: 12px">
            <h3 class="text-base font-bold text-[var(--text)]">{{ t('admin.createRole') }}</h3>
            <button
              class="p-[4px] rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
              @click="showCreate = false"
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
          <form class="space-y-[10px]" @submit.prevent="createRole">
            <div class="space-y-[4px]">
              <label class="text-xs font-medium text-zinc-400">{{ t('admin.roleName') }}</label>
              <CmkInput v-model="newRoleName" placeholder="e.g. operators" field-size="FILL" />
            </div>
            <div class="flex gap-[8px] justify-end pt-[10px] border-t border-[var(--border)]">
              <CmkButton variant="secondary" @click="showCreate = false">{{
                t('common.cancel')
              }}</CmkButton>
              <CmkButton variant="primary" @click="createRole">{{ t('common.create') }}</CmkButton>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Edit permissions dialog -->
    <Teleport to="body">
      <div v-if="editRole" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="cancelEdit" />
        <div
          class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-xl w-[28rem] max-h-[90vh] flex flex-col overflow-hidden"
        >
          <div
            class="flex items-center justify-between shrink-0 border-b border-[var(--border)]"
            style="padding: 10px 16px"
          >
            <h3 class="text-base font-bold text-[var(--text)]">
              {{ t('admin.permissionsTitle') }} –
              <span class="text-[var(--color-corporate-green-50)]">{{ editRole.name }}</span>
            </h3>
            <button
              class="p-[4px] rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
              @click="cancelEdit"
            >
              <svg
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
                style="width: 14px; height: 14px"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="overflow-y-auto flex-1 space-y-[16px]" style="padding: 10px 16px">
            <!-- Current permissions -->
            <div>
              <p class="text-xs font-medium text-zinc-500" style="margin-bottom: 6px">
                {{ t('admin.assigned') }}
              </p>
              <div
                v-if="draftPerms.length"
                class="divide-y divide-[var(--border)] rounded-lg ring-1 ring-[var(--border)] overflow-hidden"
              >
                <div
                  v-for="perm in draftPerms"
                  :key="perm.perm_id"
                  class="flex items-center justify-between gap-[8px] hover:bg-[var(--bg-hover)] transition-colors"
                  style="padding: 5px 10px"
                  :class="perm.perm_id < 0 ? 'bg-[var(--color-corporate-green-50)]/5' : ''"
                >
                  <span class="text-xs font-mono text-zinc-300"
                    >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span
                  >
                  <span
                    v-if="perm.perm_id < 0"
                    class="text-[10px] text-[var(--color-corporate-green-50)] shrink-0"
                    >new</span
                  >
                  <button
                    class="text-zinc-500 hover:text-red-400 transition-colors shrink-0 p-0.5 rounded"
                    :title="t('common.delete')"
                    @click="removeDraftPerm(perm.perm_id)"
                  >
                    <svg
                      style="width: 12px; height: 12px"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2.5"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              </div>
              <p v-else class="text-xs text-zinc-600">{{ t('admin.noPermissionsYet') }}</p>
            </div>

            <!-- Add permission form -->
            <div class="border-t border-[var(--border)] pt-[12px]">
              <p class="text-xs font-medium text-zinc-500" style="margin-bottom: 6px">
                {{ t('admin.addPermission') }}
              </p>
              <form class="space-y-[10px]" @submit.prevent="addDraftPerm">
                <div class="space-y-[4px]">
                  <label class="text-xs font-medium text-zinc-400">{{ t('admin.preset') }}</label>
                  <AppSelect
                    :model-value="permPreset"
                    :options="[
                      { value: '', label: t('admin.choosePreset') },
                      { value: 'map:view:*', label: t('admin.presetViewAll') },
                      { value: 'map:edit:*', label: t('admin.presetEditAll') },
                      { value: 'map:view:custom', label: t('admin.presetViewCustom') },
                      { value: 'map:edit:custom', label: t('admin.presetEditCustom') },
                      { value: 'user:edit:*', label: t('admin.presetEditUsers') },
                    ]"
                    @update:model-value="
                      (v) => {
                        permPreset = v;
                        applyPreset();
                      }
                    "
                  />
                </div>
                <div v-if="needsMapName" class="space-y-[4px]">
                  <label class="text-xs font-medium text-zinc-400">{{
                    t('admin.boardNameLabel')
                  }}</label>
                  <CmkInput v-model="newPerm.obj" placeholder="my-board" field-size="FILL" />
                </div>
                <p v-if="permError" class="text-red-400 text-xs">{{ permError }}</p>
                <div class="flex justify-end">
                  <button
                    type="submit"
                    :disabled="!permPreset"
                    class="bg-[var(--default-form-element-bg-color)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--default-border-color)] hover:ring-[var(--default-form-element-border-color)] disabled:opacity-50 rounded-lg text-sm font-medium text-zinc-300 transition-all"
                    style="padding: 5px 10px"
                  >
                    {{ t('admin.add') }}
                  </button>
                </div>
              </form>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="flex items-center justify-end gap-[8px] shrink-0 border-t border-[var(--border)]"
            style="padding: 8px 16px"
          >
            <p v-if="permSaveError" class="text-red-400 text-xs flex-1">{{ permSaveError }}</p>
            <CmkButton variant="secondary" @click="cancelEdit">{{ t('common.cancel') }}</CmkButton>
            <CmkButton variant="primary" :disabled="permSaving" @click="savePermissions">
              {{ permSaving ? t('common.saving') : t('common.save') }}
            </CmkButton>
          </div>
        </div>
      </div>
    </Teleport>

    <ConfirmDialog
      v-if="deleteTargetId !== null"
      :title="t('admin.deleteRole')"
      :message="t('board.cannotBeUndone')"
      :confirm-label="t('common.delete')"
      @confirm="confirmDeleteRole"
      @cancel="deleteTargetId = null"
    />
  </div>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { rolesApi } from '@/api/client';
import AppSelect from '@/components/AppSelect.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';
import type { PermissionRead, RoleRead } from '@/types/api';

const { t } = useI18n();
const auth = useAuthStore();
const toast = useToast();
const roles = ref<RoleRead[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const newRoleName = ref('');

const editRole = ref<RoleRead | null>(null);

// Draft state: local copies that have not yet been persisted
const draftPerms = ref<PermissionRead[]>([]);
const removedPermIds = ref<number[]>([]); // existing perm_ids to remove on save
let draftCounter = -1; // negative IDs for new draft entries

const newPerm = ref({ mod: '', act: '', obj: '*' });
const permSaving = ref(false);
const permSaveError = ref('');
const permError = ref('');
const permPreset = ref('');
const needsMapName = computed(() => permPreset.value.endsWith(':custom'));

function applyPreset() {
  if (!permPreset.value) return;
  if (permPreset.value.endsWith(':custom')) {
    const [mod, act] = permPreset.value.split(':');
    newPerm.value = { mod, act, obj: '' };
    return;
  }
  const [mod, act, obj] = permPreset.value.split(':');
  newPerm.value = { mod, act, obj };
}

async function fetchRoles() {
  loading.value = true;
  try {
    roles.value = await rolesApi.list(auth.accessToken!);
  } finally {
    loading.value = false;
  }
}

async function createRole() {
  try {
    await rolesApi.create(newRoleName.value, auth.accessToken!);
    showCreate.value = false;
    newRoleName.value = '';
    toast.success(t('admin.roleCreated'));
    await fetchRoles();
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : t('admin.saveFailed'));
  }
}

const deleteTargetId = ref<number | null>(null);

async function confirmDeleteRole() {
  const id = deleteTargetId.value;
  if (id === null) return;
  deleteTargetId.value = null;
  try {
    await rolesApi.delete(id, auth.accessToken!);
    toast.success(t('admin.roleDeleted'));
    await fetchRoles();
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : t('admin.deleteFailed'));
  }
}

function openEdit(role: RoleRead) {
  editRole.value = { ...role, permissions: [...role.permissions] };
  draftPerms.value = [...role.permissions];
  removedPermIds.value = [];
  newPerm.value = { mod: '', act: '', obj: '*' };
  permPreset.value = '';
  permError.value = '';
  permSaveError.value = '';
}

function cancelEdit() {
  editRole.value = null;
}

function addDraftPerm() {
  if (!editRole.value || !permPreset.value) return;
  permError.value = '';
  let mod = newPerm.value.mod;
  let act = newPerm.value.act;
  let obj = newPerm.value.obj || '*';
  if (!permPreset.value.endsWith(':custom')) {
    const parts = permPreset.value.split(':');
    mod = parts[0];
    act = parts[1];
    obj = parts[2];
  }
  if (!mod || !act || !obj) {
    permError.value = t('admin.boardNameLabel');
    return;
  }
  // Avoid duplicates in draft
  const exists = draftPerms.value.some((p) => p.mod === mod && p.act === act && p.obj === obj);
  if (exists) return;
  draftPerms.value.push({ perm_id: draftCounter--, mod, act, obj });
  permPreset.value = '';
  newPerm.value = { mod: '', act: '', obj: '*' };
}

function removeDraftPerm(permId: number) {
  if (permId > 0) {
    // existing server perm — mark for removal
    removedPermIds.value.push(permId);
  }
  draftPerms.value = draftPerms.value.filter((p) => p.perm_id !== permId);
}

async function savePermissions() {
  if (!editRole.value) return;
  permSaving.value = true;
  permSaveError.value = '';
  try {
    const roleId = editRole.value.role_id;
    // Remove permissions that were deleted in draft
    for (const permId of removedPermIds.value) {
      await rolesApi.removePermission(roleId, permId, auth.accessToken!);
    }
    // Add new permissions (draft entries with negative perm_id)
    for (const perm of draftPerms.value) {
      if (perm.perm_id < 0) {
        let existing: PermissionRead | null = null;
        for (const r of roles.value) {
          const p = r.permissions.find(
            (p) => p.mod === perm.mod && p.act === perm.act && p.obj === perm.obj,
          );
          if (p) {
            existing = p;
            break;
          }
        }
        if (!existing) {
          existing = await rolesApi.createPermission(
            perm.mod,
            perm.act,
            perm.obj,
            auth.accessToken!,
          );
        }
        await rolesApi.assignPermission(roleId, existing.perm_id, auth.accessToken!);
      }
    }
    await fetchRoles();
    editRole.value = null;
  } catch (e: unknown) {
    permSaveError.value = e instanceof Error ? e.message : t('admin.failedToAddPermission');
  } finally {
    permSaving.value = false;
  }
}

onMounted(fetchRoles);
</script>
