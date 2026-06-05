<template>
    <div class="orb-roles">
        <div class="orb-roles__header">
            <div>
                <CmkHeading type="h2">
                    {{ t('admin.rolesAndPermissions') }}
                </CmkHeading>
                <CmkParagraph class="admin-subtitle">
                    {{ t('admin.rolesSubtitle') }}
                </CmkParagraph>
            </div>
            <CmkButton variant="primary" @click="showCreate = true">
                <svg
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                    style="width: 13px; height: 13px; margin-right: var(--dimension-3)"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 4.5v15m7.5-7.5h-15"
                    />
                </svg>
                {{ t('admin.newRole') }}
            </CmkButton>
        </div>

        <div v-if="loading" class="orb-roles__loading">
            <CmkLoading />
        </div>

        <div v-else class="orb-roles__list">
            <div v-for="role in roles" :key="role.role_id" class="orb-roles__card">
                <div class="orb-roles__card-row">
                    <div class="orb-roles__card-main">
                        <div class="orb-roles__title-row">
                            <span class="orb-roles__name">{{ role.name }}</span>
                            <span class="orb-roles__count">
                                {{ role.permissions.length }} {{ t('admin.permissions') }}
                            </span>
                        </div>
                        <div v-if="role.permissions.length" class="orb-roles__perms">
                            <span
                                v-for="perm in role.permissions"
                                :key="perm.perm_id"
                                class="orb-roles__perm-chip"
                                >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span
                            >
                        </div>
                        <p v-else class="orb-roles__no-perms">
                            {{ t('admin.noPermissions') }}
                        </p>
                    </div>
                    <div class="orb-roles__actions">
                        <button
                            class="orb-roles__action-btn orb-roles__action-btn--edit"
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
                            class="orb-roles__action-btn orb-roles__action-btn--delete"
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

            <div v-if="!roles.length" class="orb-roles__empty">
                {{ t('admin.noRoles') }}
            </div>
        </div>

        <OrbModal
            :open="showCreate"
            :title="t('admin.createRole')"
            closable
            @close="showCreate = false"
        >
            <form class="roles-create__form" @submit.prevent="createRole">
                <div class="roles-create__field">
                    <label class="roles-create__label">{{ t('admin.roleName') }}</label>
                    <CmkInput
                        v-model="newRoleName"
                        placeholder="e.g. operators"
                        field-size="FILL"
                    />
                </div>
            </form>
            <template #footer>
                <CmkButton variant="secondary" @click="showCreate = false">
                    {{ t('common.cancel') }}
                </CmkButton>
                <CmkButton variant="primary" @click="createRole">
                    {{ t('common.create') }}
                </CmkButton>
            </template>
        </OrbModal>

        <OrbModal :open="!!editRole" closable @close="cancelEdit">
            <template #header>
                <span class="roles-edit__title">
                    {{ t('admin.permissionsTitle') }} –
                    <span class="roles-edit__name">{{ editRole?.name }}</span>
                </span>
            </template>
            <div v-if="editRole" class="roles-edit__body">
                <!-- Current permissions -->
                <div>
                    <p class="roles-edit__group-label">
                        {{ t('admin.assigned') }}
                    </p>
                    <div v-if="draftPerms.length" class="roles-edit__perm-list">
                        <div
                            v-for="perm in draftPerms"
                            :key="perm.perm_id"
                            class="roles-edit__perm-row"
                            :class="perm.perm_id < 0 ? 'roles-edit__perm-row--new' : ''"
                        >
                            <span class="roles-edit__perm-text"
                                >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span
                            >
                            <span v-if="perm.perm_id < 0" class="roles-edit__perm-new">new</span>
                            <button
                                class="roles-edit__perm-remove"
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
                    <p v-else class="roles-edit__hint">
                        {{ t('admin.noPermissionsYet') }}
                    </p>
                </div>

                <!-- Add permission form -->
                <div class="roles-edit__add-section">
                    <p class="roles-edit__group-label">
                        {{ t('admin.addPermission') }}
                    </p>
                    <form class="roles-edit__add-form" @submit.prevent="addDraftPerm">
                        <div class="roles-edit__field">
                            <label class="roles-edit__label">{{ t('admin.preset') }}</label>
                            <CmkDropdown
                                :selected-option="permPreset"
                                :options="permPresetOptions"
                                :width="'fill'"
                                :label="t('admin.preset')"
                                @update:selected-option="
                                    (v) => {
                                        permPreset = v ?? '';
                                        applyPreset();
                                    }
                                "
                            />
                        </div>
                        <div v-if="needsMapName" class="roles-edit__field">
                            <label class="roles-edit__label">{{ t('admin.boardNameLabel') }}</label>
                            <CmkInput
                                v-model="newPerm.obj"
                                placeholder="my-board"
                                field-size="FILL"
                            />
                        </div>
                        <p v-if="permError" class="roles-edit__form-error">
                            {{ permError }}
                        </p>
                        <div class="roles-edit__add-actions">
                            <button
                                type="submit"
                                :disabled="!permPreset"
                                class="roles-edit__add-btn"
                            >
                                {{ t('admin.add') }}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            <template #footer>
                <p v-if="permSaveError" class="roles-edit__error">{{ permSaveError }}</p>
                <CmkButton variant="secondary" @click="cancelEdit">
                    {{ t('common.cancel') }}
                </CmkButton>
                <CmkButton variant="primary" :disabled="permSaving" @click="savePermissions">
                    {{ permSaving ? t('common.saving') : t('common.save') }}
                </CmkButton>
            </template>
        </OrbModal>

        <OrbConfirmDialog
            :open="deleteTargetId !== null"
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
import CmkButton from '@/components/cmk/CmkButton';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import CmkLoading from '@/components/cmk/CmkLoading';
import CmkHeading from '@/components/cmk/typography/CmkHeading';
import CmkParagraph from '@/components/cmk/typography/CmkParagraph';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue';
import OrbModal from '@/components/OrbModal.vue';
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
const permPresetOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: '', title: t('admin.choosePreset') },
        { name: 'map:view:*', title: t('admin.presetViewAll') },
        { name: 'map:edit:*', title: t('admin.presetEditAll') },
        { name: 'map:view:custom', title: t('admin.presetViewCustom') },
        { name: 'map:edit:custom', title: t('admin.presetEditCustom') },
        { name: 'user:edit:*', title: t('admin.presetEditUsers') },
    ],
}));

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

<style scoped>
.orb-roles {
    max-width: 768px;
}

.orb-roles__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--dimension-6);
}

.orb-roles__loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px 0;
}

.orb-roles__list > * + * {
    margin-top: var(--dimension-4);
}

.orb-roles__card {
    padding: var(--dimension-5);
    background: var(--bg-surface);
    border-radius: 12px;
    box-shadow: 0 0 0 1px var(--border);
}

.orb-roles__card-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--dimension-5);
}

.orb-roles__card-main {
    flex: 1;
    min-width: 0;
}

.orb-roles__title-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 3px;
}

.orb-roles__name {
    font-weight: 600;
    color: var(--text);
}

.orb-roles__count {
    padding: 1px 5px;
    font-size: var(--font-size-normal);
    line-height: 16px;
    color: var(--text-muted);
    background: var(--default-form-element-bg-color);
    border-radius: 4px;
    box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.orb-roles__perms {
    display: flex;
    flex-wrap: wrap;
    gap: var(--dimension-3);
    margin-top: var(--dimension-4);
}

.orb-roles__perm-chip {
    padding: 1px 5px;
    font-family:
        ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
        monospace;
    font-size: var(--font-size-normal);
    line-height: 16px;
    color: var(--text-muted);
    background: var(--default-form-element-bg-color);
    border-radius: 6px;
    box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.orb-roles__no-perms {
    margin-top: 6px;
    font-size: var(--font-size-large);
    line-height: 20px;
    color: var(--text-muted);
}

.orb-roles__actions {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 3px;
}

.orb-roles__action-btn {
    padding: var(--dimension-3);
    color: var(--text-muted);
    border-radius: 6px;
    transition: all 0.15s;
}

.orb-roles__action-btn--edit:hover {
    color: var(--color-corporate-green-50);
    background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-roles__action-btn--delete:hover {
    color: var(--color-light-red-40);
    background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}

.orb-roles__empty {
    padding: 32px 0;
    font-size: var(--font-size-large);
    line-height: 20px;
    text-align: center;
    color: var(--text-muted);
}

.roles-create__form {
    display: flex;
    flex-direction: column;
    min-width: 320px;
}

.roles-create__field {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-3);
}

.roles-create__label {
    font-size: var(--font-size-large);
    font-weight: 500;
    color: var(--text-muted);
}

.roles-edit__title {
    font-size: var(--font-size-large);
    font-weight: var(--font-weight-bold);
}

.roles-edit__name {
    color: var(--color-corporate-green-50);
}

.roles-edit__body {
    width: min(28rem, 90vw);
    max-height: 60vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--dimension-6);
}

.roles-edit__error {
    font-size: var(--font-size-normal);
    color: var(--color-light-red-40);
    flex: 1;
}

.roles-edit__group-label {
    margin-bottom: 6px;
    font-size: var(--font-size-large);
    line-height: 20px;
    font-weight: 500;
    color: var(--text-muted);
}

.roles-edit__perm-list {
    overflow: hidden;
    border-radius: 8px;
    box-shadow: 0 0 0 1px var(--border);
}

.roles-edit__perm-list > * + * {
    border-top: 1px solid var(--border);
}

.roles-edit__perm-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--dimension-4);
    padding: 5px 10px;
    transition: background-color 0.15s;
}

.roles-edit__perm-row--new {
    background: color-mix(in srgb, var(--color-corporate-green-50) 5%, transparent);
}

.roles-edit__perm-row:hover {
    background: var(--bg-hover);
}

.roles-edit__perm-text {
    font-family:
        ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
        monospace;
    font-size: var(--font-size-normal);
    line-height: 16px;
    color: var(--text);
}

.roles-edit__perm-new {
    flex-shrink: 0;
    font-size: var(--font-size-normal);
    line-height: 16px;
    font-weight: 500;
    color: var(--color-corporate-green-50);
}

.roles-edit__perm-remove {
    flex-shrink: 0;
    padding: var(--dimension-2);
    color: var(--text-muted);
    border-radius: 4px;
    transition: color 0.15s;
}

.roles-edit__perm-remove:hover {
    color: var(--color-light-red-40);
}

.roles-edit__hint {
    font-size: var(--font-size-large);
    line-height: 20px;
    color: var(--text-muted);
}

.roles-edit__add-section {
    padding-top: var(--dimension-5);
    border-top: 1px solid var(--border);
}

.roles-edit__add-form > * + * {
    margin-top: 10px;
}

.roles-edit__field > * + * {
    margin-top: var(--dimension-3);
}

.roles-edit__label {
    font-size: var(--font-size-large);
    line-height: 20px;
    font-weight: 500;
    color: var(--text-muted);
}

.roles-edit__form-error {
    font-size: var(--font-size-large);
    line-height: 20px;
    color: var(--color-light-red-40);
}

.roles-edit__add-actions {
    display: flex;
    justify-content: flex-end;
}

.roles-edit__add-btn {
    padding: 5px 10px;
    font-size: var(--font-size-large);
    line-height: 20px;
    font-weight: 500;
    color: var(--text);
    background: var(--default-form-element-bg-color);
    border-radius: 8px;
    box-shadow: 0 0 0 1px var(--default-border-color);
    transition: all 0.15s;
}

.roles-edit__add-btn:hover {
    background: var(--bg-hover);
    box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.roles-edit__add-btn:disabled {
    opacity: 0.5;
}
</style>
