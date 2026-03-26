<template>
  <div class="max-w-3xl">
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">
          {{ t('admin.rolesAndPermissions') }}
        </h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('admin.rolesSubtitle') }}</p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 ring-1 ring-zinc-700 hover:ring-zinc-500 rounded-lg text-sm font-medium text-zinc-300 hover:text-[var(--text)] transition-all duration-150"
        @click="showCreate = true"
      >
        <svg
          class="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('admin.newRole') }}
      </button>
    </div>

    <div v-if="loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="role in roles"
        :key="role.role_id"
        class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-5 hover:ring-[var(--border)] transition-all"
      >
        <div class="flex justify-between items-start gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2.5 mb-1">
              <span class="font-semibold text-[var(--text)]">{{ role.name }}</span>
              <span
                class="text-xs px-1.5 py-0.5 rounded bg-[var(--bg-input)] ring-1 ring-zinc-700 text-zinc-500"
              >
                {{ role.permissions.length }} {{ t('admin.permissions') }}
              </span>
            </div>
            <div v-if="role.permissions.length" class="flex flex-wrap gap-1.5 mt-2.5">
              <span
                v-for="perm in role.permissions"
                :key="perm.perm_id"
                class="text-xs bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-md px-2 py-0.5 text-zinc-400 font-mono"
                >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span
              >
            </div>
            <p v-else class="text-xs text-zinc-600 mt-2">{{ t('admin.noPermissions') }}</p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button
              class="p-1.5 rounded-md text-zinc-600 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
              :title="t('common.edit')"
              @click="openEdit(role)"
            >
              <svg
                class="w-3.5 h-3.5"
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
              class="p-1.5 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
              :title="t('common.delete')"
              @click="deleteTargetId = role.role_id"
            >
              <svg
                class="w-3.5 h-3.5"
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
        </div>
      </div>

      <div v-if="!roles.length" class="text-center py-12 text-zinc-600 text-sm">
        {{ t('admin.noRoles') }}
      </div>
    </div>

    <!-- Create role dialog -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreate = false" />
        <div
          class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-80"
        >
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-bold text-[var(--text)]">{{ t('admin.createRole') }}</h3>
            <button
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
              @click="showCreate = false"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <form class="space-y-4" @submit.prevent="createRole">
            <div class="space-y-1.5">
              <label class="text-xs font-medium text-zinc-400">{{ t('admin.roleName') }}</label>
              <input
                v-model="newRoleName"
                placeholder="e.g. operators"
                required
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
              />
            </div>
            <div class="flex gap-3 justify-end pt-2 border-t border-[var(--border)]">
              <button
                type="button"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
                @click="showCreate = false"
              >
                {{ t('common.cancel') }}
              </button>
              <button
                type="submit"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all"
              >
                {{ t('common.create') }}
              </button>
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
          class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl w-[28rem] max-h-[90vh] flex flex-col overflow-hidden"
        >
          <div
            class="flex items-center justify-between px-6 pt-5 pb-4 shrink-0 border-b border-[var(--border)]"
          >
            <h3 class="text-base font-bold text-[var(--text)]">
              {{ t('admin.permissionsTitle') }} –
              <span class="text-indigo-400">{{ editRole.name }}</span>
            </h3>
            <button
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
              @click="cancelEdit"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="overflow-y-auto flex-1 px-6 py-5 space-y-5">
            <!-- Current permissions -->
            <div>
              <p class="text-xs font-medium text-zinc-500 mb-3">{{ t('admin.assigned') }}</p>
              <div
                v-if="draftPerms.length"
                class="divide-y divide-[var(--border)] rounded-lg ring-1 ring-[var(--border)] overflow-hidden"
              >
                <div
                  v-for="perm in draftPerms"
                  :key="perm.perm_id"
                  class="flex items-center justify-between gap-2 px-3 py-2.5 hover:bg-[var(--bg-hover)] transition-colors"
                  :class="perm.perm_id < 0 ? 'bg-indigo-500/5' : ''"
                >
                  <span class="text-xs font-mono text-zinc-300"
                    >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span
                  >
                  <span v-if="perm.perm_id < 0" class="text-[10px] text-indigo-400 shrink-0"
                    >new</span
                  >
                  <button
                    class="text-zinc-500 hover:text-red-400 transition-colors shrink-0 p-0.5 rounded"
                    :title="t('common.delete')"
                    @click="removeDraftPerm(perm.perm_id)"
                  >
                    <svg
                      class="w-3.5 h-3.5"
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
            <div class="border-t border-[var(--border)] pt-4">
              <p class="text-xs font-medium text-zinc-500 mb-3">{{ t('admin.addPermission') }}</p>
              <form class="space-y-3" @submit.prevent="addDraftPerm">
                <div class="space-y-1.5">
                  <label class="text-xs font-medium text-zinc-400">{{ t('admin.preset') }}</label>
                  <div class="relative">
                    <select
                      v-model="permPreset"
                      class="w-full appearance-none px-3 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                      @change="applyPreset"
                    >
                      <option value="">{{ t('admin.choosePreset') }}</option>
                      <option value="map:view:*">{{ t('admin.presetViewAll') }}</option>
                      <option value="map:edit:*">{{ t('admin.presetEditAll') }}</option>
                      <option value="map:view:custom">{{ t('admin.presetViewCustom') }}</option>
                      <option value="map:edit:custom">{{ t('admin.presetEditCustom') }}</option>
                      <option value="user:edit:*">{{ t('admin.presetEditUsers') }}</option>
                    </select>
                    <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                      <svg
                        class="w-4 h-4 text-zinc-400"
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
                    </div>
                  </div>
                </div>
                <div v-if="needsMapName" class="space-y-1.5">
                  <label class="text-xs font-medium text-zinc-400">{{
                    t('admin.boardNameLabel')
                  }}</label>
                  <input
                    v-model="newPerm.obj"
                    placeholder="my-board"
                    required
                    class="w-full px-3 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                  />
                </div>
                <p v-if="permError" class="text-red-400 text-xs">{{ permError }}</p>
                <div class="flex justify-end">
                  <button
                    type="submit"
                    :disabled="!permPreset"
                    class="px-4 py-2 bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] ring-1 ring-zinc-700 hover:ring-zinc-500 disabled:opacity-50 rounded-lg text-sm font-medium text-zinc-300 transition-all"
                  >
                    {{ t('admin.add') }}
                  </button>
                </div>
              </form>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="flex items-center justify-end gap-3 px-6 py-4 shrink-0 border-t border-[var(--border)]"
          >
            <p v-if="permSaveError" class="text-red-400 text-xs flex-1">{{ permSaveError }}</p>
            <button
              class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
              @click="cancelEdit"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              :disabled="permSaving"
              class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-white transition-all"
              @click="savePermissions"
            >
              {{ permSaving ? t('common.saving') : t('common.save') }}
            </button>
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
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { rolesApi } from '@/api/client';
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
