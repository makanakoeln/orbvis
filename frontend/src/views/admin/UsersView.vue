<template>
    <div class="max-w-4xl">
        <div class="flex justify-between items-center" style="margin-bottom: 16px">
            <div>
                <CmkHeading type="h2">
                    {{ t('admin.users') }}
                </CmkHeading>
                <CmkParagraph class="admin-subtitle">
                    {{ t('admin.usersSubtitle') }}
                </CmkParagraph>
            </div>
            <CmkButton variant="primary" @click="showCreate = true">
                <svg
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                    style="width: 13px; height: 13px; margin-right: 4px"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 4.5v15m7.5-7.5h-15"
                    />
                </svg>
                {{ t('admin.newUser') }}
            </CmkButton>
        </div>

        <div v-if="loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <div
            v-else
            class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
        >
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b border-[var(--border)]">
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.name') }}
                        </th>
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.type') }}
                        </th>
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.status') }}
                        </th>
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.roles') }}
                        </th>
                        <th
                            class="text-right text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.actions') }}
                        </th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-[var(--border)]">
                    <tr
                        v-for="user in users"
                        :key="user.user_id"
                        class="hover:bg-[var(--bg-hover)] transition-colors"
                    >
                        <td class="font-medium text-[var(--text)]" style="padding: 6px 12px">
                            {{ user.name }}
                        </td>
                        <td style="padding: 6px 12px">
                            <CmkBadge
                                v-if="user.is_admin"
                                size="small"
                                type="outline"
                                color="warning"
                                >{{ t('admin.admin') }}</CmkBadge
                            >
                            <span v-else class="text-sm text-[var(--text-muted)]">{{
                                t('admin.user')
                            }}</span>
                        </td>
                        <td style="padding: 6px 12px">
                            <span
                                class="inline-flex items-center gap-[4px] text-xs font-medium"
                                :class="user.is_active ? 'text-green-400' : 'text-red-400'"
                            >
                                <span
                                    class="rounded-full"
                                    style="width: 6px; height: 6px"
                                    :class="user.is_active ? 'bg-green-400' : 'bg-red-400'"
                                />
                                {{ user.is_active ? t('admin.active') : t('admin.inactive') }}
                            </span>
                        </td>
                        <td class="text-[var(--text-muted)] text-sm" style="padding: 6px 12px">
                            <template v-if="user.roles.length">
                                <span
                                    v-for="r in user.roles"
                                    :key="r.role_id"
                                    class="inline-block rounded bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] text-[var(--text-muted)] mr-1 mb-0.5"
                                    style="padding: 1px 5px"
                                >
                                    {{ r.name }}
                                </span>
                            </template>
                            <span v-else class="text-[var(--text-muted)]">—</span>
                        </td>
                        <td class="text-right" style="padding: 6px 12px">
                            <div class="flex items-center justify-end gap-[3px]">
                                <template v-if="user.user_id !== auth.user?.user_id">
                                    <button
                                        v-if="canEditUsers"
                                        class="p-[4px] rounded-md text-[var(--text-muted)] hover:text-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-50)]/10 transition-all"
                                        :title="t('common.edit')"
                                        @click="editUser = user"
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
                                        class="p-[4px] rounded-md text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-all"
                                        :title="t('common.delete')"
                                        @click="deleteTargetId = user.user_id"
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
                                </template>
                                <span v-else class="text-xs text-[var(--text-muted)] pr-1">—</span>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <OrbModal
            :open="showCreate"
            :title="t('admin.createUser')"
            closable
            @close="showCreate = false"
        >
            <form class="users-create__form" @submit.prevent="createUser">
                <div class="space-y-[4px]">
                    <CmkLabel>{{ t('auth.username') }}</CmkLabel>
                    <CmkInput
                        v-model="newUser.name"
                        placeholder="john"
                        autocomplete="off"
                        field-size="FILL"
                    />
                </div>

                <div class="space-y-[4px]">
                    <CmkLabel>{{ t('auth.password') }}</CmkLabel>
                    <CmkInput
                        v-model="newUser.password"
                        type="password"
                        autocomplete="new-password"
                        field-size="FILL"
                    />
                    <p class="text-sm text-[var(--text-muted)]">
                        {{ t('userSettings.passwordMinLength') }}
                    </p>
                </div>

                <div class="space-y-[4px]">
                    <CmkLabel>{{ t('userSettings.confirmPassword') }}</CmkLabel>
                    <CmkInput
                        v-model="newUserConfirmPassword"
                        type="password"
                        autocomplete="new-password"
                        field-size="FILL"
                    />
                    <p
                        v-if="newUserConfirmPassword && newUser.password !== newUserConfirmPassword"
                        class="text-xs text-red-400"
                    >
                        {{ t('userSettings.passwordMismatch') }}
                    </p>
                </div>

                <div class="border-t border-[var(--border)] pt-[10px] space-y-[10px]">
                    <div class="flex items-start gap-[8px]">
                        <CmkCheckbox v-model="newUser.is_admin" :label="t('admin.administrator')" />
                        <p class="text-sm text-[var(--text-muted)] mt-0.5">
                            {{ t('admin.administratorHint') }}
                        </p>
                    </div>

                    <CmkCheckbox
                        v-model="newUser.must_change_password"
                        :label="t('admin.mustChangePassword')"
                    />
                </div>

                <div
                    v-if="availableRoles.length"
                    class="border-t border-[var(--border)] pt-[10px] space-y-[8px]"
                >
                    <p class="text-sm font-medium text-[var(--text-muted)]">
                        {{ t('admin.roles') }}
                    </p>
                    <div v-for="role in availableRoles" :key="role.role_id">
                        <CmkCheckbox
                            :model-value="selectedRoleIds.includes(role.role_id)"
                            :label="role.name"
                            @update:model-value="
                                (v) => {
                                    if (v) selectedRoleIds.push(role.role_id);
                                    else
                                        selectedRoleIds = selectedRoleIds.filter(
                                            (id) => id !== role.role_id,
                                        );
                                }
                            "
                        />
                    </div>
                </div>

                <p v-if="createError" class="users-create__error">{{ createError }}</p>
            </form>
            <template #footer>
                <CmkButton variant="secondary" @click="showCreate = false">
                    {{ t('common.cancel') }}
                </CmkButton>
                <CmkButton
                    variant="primary"
                    :disabled="creating || newUser.password !== newUserConfirmPassword"
                    @click="createUser"
                >
                    {{ creating ? t('common.saving') : t('common.create') }}
                </CmkButton>
            </template>
        </OrbModal>

        <OrbConfirmDialog
            :open="deleteTargetId !== null"
            :title="t('admin.deleteUser')"
            :message="t('board.cannotBeUndone')"
            :confirm-label="t('common.delete')"
            @confirm="confirmDeleteUser"
            @cancel="deleteTargetId = null"
        />

        <UserSettingsPanel
            v-if="editUser"
            :user-id="editUser.user_id"
            :user-name="editUser.name"
            :is-self="false"
            :user-read="editUser"
            :available-roles="availableRoles"
            @close="
                editUser = null;
                fetchUsers();
            "
        />
    </div>
</template>

<script setup lang="ts">
import CmkBadge from '@cmk/components/CmkBadge.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { rolesApi, usersApi } from '@/api/client';
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue';
import OrbModal from '@/components/OrbModal.vue';
import UserSettingsPanel from '@/components/UserSettingsPanel.vue';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';
import type { RoleRead, UserRead } from '@/types/api';

const { t } = useI18n();
const auth = useAuthStore();
const toast = useToast();
const users = ref<UserRead[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const creating = ref(false);
const createError = ref('');
const newUser = ref({ name: '', password: '', is_admin: false, must_change_password: false });
const newUserConfirmPassword = ref('');
const editUser = ref<UserRead | null>(null);
const availableRoles = ref<RoleRead[]>([]);
const selectedRoleIds = ref<number[]>([]);

watch(showCreate, (open) => {
    if (!open) return;
    selectedRoleIds.value = [];
    newUserConfirmPassword.value = '';
});
const canEditUsers = computed(
    () =>
        auth.user?.is_admin ||
        (auth.user?.permissions?.some(
            (p) => p.mod === 'user' && p.act === 'edit' && p.obj === '*',
        ) ??
            false),
);

async function fetchUsers() {
    loading.value = true;
    try {
        users.value = await usersApi.list(auth.accessToken!);
    } finally {
        loading.value = false;
    }
}

async function createUser() {
    if (newUser.value.password !== newUserConfirmPassword.value) return;
    creating.value = true;
    createError.value = '';
    try {
        const created = await usersApi.create(newUser.value, auth.accessToken!);
        await Promise.all(
            selectedRoleIds.value.map((rid) =>
                usersApi.assignRole(created.user_id, rid, auth.accessToken!),
            ),
        );
        showCreate.value = false;
        newUser.value = { name: '', password: '', is_admin: false, must_change_password: false };
        toast.success(t('admin.userCreated', { name: created.name }));
        await fetchUsers();
    } catch (e: unknown) {
        createError.value = e instanceof Error ? e.message : t('admin.saveFailed');
    } finally {
        creating.value = false;
    }
}

const deleteTargetId = ref<number | null>(null);

async function confirmDeleteUser() {
    const id = deleteTargetId.value;
    if (id === null) return;
    deleteTargetId.value = null;
    try {
        await usersApi.delete(id, auth.accessToken!);
        toast.success(t('admin.userDeleted'));
        await fetchUsers();
    } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : t('admin.deleteFailed'));
    }
}

async function loadRoles() {
    availableRoles.value = await rolesApi.list(auth.accessToken!);
}

onMounted(() => {
    fetchUsers();
    loadRoles();
});
</script>

<style scoped>
.users-create__form {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-5);
    min-width: 380px;
}

.users-create__error {
    font-size: var(--font-size-normal);
    color: var(--color-light-red-40);
}
</style>
