<template>
  <div class="orb-users">
    <div class="orb-users__header">
      <div>
        <CmkHeading type="h2">
          {{ _t('Users') }}
        </CmkHeading>
        <CmkParagraph class="admin-subtitle">
          {{ _t('Manage user accounts and permissions') }}
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
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ _t('New User') }}
      </CmkButton>
    </div>

    <div v-if="loading" class="orb-users__loading">
      <CmkLoading />
    </div>

    <div v-else class="orb-users__card">
      <table class="orb-users__table">
        <thead>
          <tr class="orb-users__head-row">
            <th class="orb-users__th">
              {{ _t('Name') }}
            </th>
            <th class="orb-users__th">
              {{ _t('Type') }}
            </th>
            <th class="orb-users__th">
              {{ _t('Status') }}
            </th>
            <th class="orb-users__th">
              {{ _t('Roles') }}
            </th>
            <th class="orb-users__th orb-users__th--right">
              {{ _t('Actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="orb-users__body">
          <tr v-for="user in users" :key="user.user_id" class="orb-users__row">
            <td class="orb-users__td orb-users__td--name">
              {{ user.name }}
            </td>
            <td class="orb-users__td">
              <CmkBadge v-if="user.is_admin" size="small" type="outline" color="warning">{{
                _t('Admin')
              }}</CmkBadge>
              <span v-else class="orb-users__user-type">{{ _t('User') }}</span>
            </td>
            <td class="orb-users__td">
              <span
                class="orb-users__status"
                :class="
                  user.is_active ? 'orb-users__status--active' : 'orb-users__status--inactive'
                "
              >
                <span class="orb-users__status-dot" />
                {{ user.is_active ? _t('Active') : _t('Inactive') }}
              </span>
            </td>
            <td class="orb-users__td orb-users__td--roles">
              <template v-if="user.roles.length">
                <span v-for="r in user.roles" :key="r.role_id" class="orb-users__role-chip">
                  {{ r.name }}
                </span>
              </template>
              <span v-else>—</span>
            </td>
            <td class="orb-users__td orb-users__td--right">
              <div class="orb-users__actions">
                <template v-if="user.user_id !== auth.user?.user_id">
                  <button
                    v-if="canEditUsers"
                    class="orb-users__action-btn orb-users__action-btn--edit"
                    :title="_t('Edit')"
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
                    class="orb-users__action-btn orb-users__action-btn--delete"
                    :title="_t('Delete')"
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
                <span v-else class="orb-users__self-dash">—</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <OrbModal :open="showCreate" :title="_t('Create User')" closable @close="showCreate = false">
      <form class="users-create__form" @submit.prevent="createUser">
        <div class="users-create__field">
          <CmkLabel>{{ _t('Username') }}</CmkLabel>
          <CmkInput
            v-model="newUser.name"
            placeholder="john"
            autocomplete="off"
            field-size="FILL"
          />
        </div>

        <div class="users-create__field">
          <CmkLabel>{{ _t('Password') }}</CmkLabel>
          <CmkInput
            v-model="newUser.password"
            type="password"
            autocomplete="new-password"
            field-size="FILL"
          />
          <p class="users-create__hint">
            {{ _t('At least 6 characters') }}
          </p>
        </div>

        <div class="users-create__field">
          <CmkLabel>{{ _t('Confirm password') }}</CmkLabel>
          <CmkInput
            v-model="newUserConfirmPassword"
            type="password"
            autocomplete="new-password"
            field-size="FILL"
          />
          <p
            v-if="newUserConfirmPassword && newUser.password !== newUserConfirmPassword"
            class="users-create__mismatch"
          >
            {{ _t('Passwords do not match.') }}
          </p>
        </div>

        <div class="users-create__section">
          <div class="users-create__checkbox-row">
            <CmkCheckbox v-model="newUser.is_admin" :label="_t('Administrator')" />
            <p class="users-create__checkbox-hint">
              {{ _t('Full access to all admin functions') }}
            </p>
          </div>

          <CmkCheckbox
            v-model="newUser.must_change_password"
            :label="_t('Must change password on next login')"
          />
        </div>

        <div
          v-if="availableRoles.length"
          class="users-create__section users-create__section--roles"
        >
          <p class="users-create__group-label">
            {{ _t('Roles') }}
          </p>
          <div v-for="role in availableRoles" :key="role.role_id">
            <CmkCheckbox
              :model-value="selectedRoleIds.includes(role.role_id)"
              :label="role.name"
              @update:model-value="
                (v) => {
                  if (v) selectedRoleIds.push(role.role_id)
                  else selectedRoleIds = selectedRoleIds.filter((id) => id !== role.role_id)
                }
              "
            />
          </div>
        </div>

        <p v-if="createError" class="users-create__error">{{ createError }}</p>
      </form>
      <template #footer>
        <CmkButton variant="secondary" @click="showCreate = false">
          {{ _t('Cancel') }}
        </CmkButton>
        <CmkButton
          variant="primary"
          :disabled="creating || newUser.password !== newUserConfirmPassword"
          @click="createUser"
        >
          {{ creating ? _t('Saving…') : _t('Create') }}
        </CmkButton>
      </template>
    </OrbModal>

    <OrbConfirmDialog
      :open="deleteTargetId !== null"
      :title="_t('Delete this user?')"
      :message="_t('This cannot be undone.')"
      :confirm-label="_t('Delete')"
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
      @close="closeEditUser"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import OrbModal from '@/components/OrbModal.vue'
import UserSettingsPanel from '@/components/UserSettingsPanel.vue'
import CmkBadge from '@/components/cmk/CmkBadge'
import CmkButton from '@/components/cmk/CmkButton'
import CmkLabel from '@/components/cmk/CmkLabel'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkHeading from '@/components/cmk/typography/CmkHeading'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { rolesApi, usersApi } from '@/api/client'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import type { RoleRead, UserRead } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()
const auth = useAuthStore()
const toast = useToast()
const users = ref<UserRead[]>([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const newUser = ref({ name: '', password: '', is_admin: false, must_change_password: false })
const newUserConfirmPassword = ref('')
const editUser = ref<UserRead | null>(null)
const availableRoles = ref<RoleRead[]>([])
const selectedRoleIds = ref<number[]>([])

watch(showCreate, (open) => {
  if (!open) return
  selectedRoleIds.value = []
  newUserConfirmPassword.value = ''
})
const canEditUsers = computed(
  () =>
    auth.user?.is_admin ||
    (auth.user?.permissions?.some((p) => p.mod === 'user' && p.act === 'edit' && p.obj === '*') ??
      false)
)

async function fetchUsers() {
  loading.value = true
  try {
    users.value = await usersApi.list(auth.accessToken!)
  } finally {
    loading.value = false
  }
}

async function createUser() {
  if (newUser.value.password !== newUserConfirmPassword.value) return
  creating.value = true
  createError.value = ''
  try {
    const created = await usersApi.create(newUser.value, auth.accessToken!)
    await Promise.all(
      selectedRoleIds.value.map((rid) =>
        usersApi.assignRole(created.user_id, rid, auth.accessToken!)
      )
    )
    showCreate.value = false
    newUser.value = { name: '', password: '', is_admin: false, must_change_password: false }
    toast.success(_t('User "%{name}" created', { name: created.name }))
    await fetchUsers()
  } catch (e: unknown) {
    createError.value = e instanceof Error ? e.message : _t('Save failed')
  } finally {
    creating.value = false
  }
}

const deleteTargetId = ref<number | null>(null)

async function confirmDeleteUser() {
  const id = deleteTargetId.value
  if (id === null) return
  deleteTargetId.value = null
  try {
    await usersApi.delete(id, auth.accessToken!)
    toast.success(_t('User deleted'))
    await fetchUsers()
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : _t('Delete failed'))
  }
}

async function loadRoles() {
  availableRoles.value = await rolesApi.list(auth.accessToken!)
}

onMounted(() => {
  fetchUsers()
  loadRoles()
})

function closeEditUser(): void {
  editUser.value = null
  fetchUsers()
}
</script>

<style scoped>
.orb-users {
  max-width: 896px;
}

.orb-users__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--dimension-6);
}

.orb-users__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.orb-users__card {
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-users__table {
  width: 100%;
  font-size: var(--font-size-large);
  line-height: 20px;
}

.orb-users__head-row {
  border-bottom: 1px solid var(--border);
}

.orb-users__th {
  padding: 6px 12px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-align: left;
  color: var(--text-muted);
}

.orb-users__th--right {
  text-align: right;
}

.orb-users__body > tr + tr {
  border-top: 1px solid var(--border);
}

.orb-users__row {
  transition: background-color 0.15s;
}

.orb-users__row:hover {
  background: var(--bg-hover);
}

.orb-users__td {
  padding: 6px 12px;
}

.orb-users__td--name {
  font-weight: 500;
  color: var(--text);
}

.orb-users__td--roles {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-users__td--right {
  text-align: right;
}

.orb-users__user-type {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-users__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
}

.orb-users__status--active {
  color: var(--color-corporate-green-50);
}

.orb-users__status--inactive {
  color: var(--color-light-red-40);
}

.orb-users__status-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.orb-users__status--active .orb-users__status-dot {
  background: var(--color-corporate-green-50);
}

.orb-users__status--inactive .orb-users__status-dot {
  background: var(--color-light-red-40);
}

.orb-users__role-chip {
  display: inline-block;
  padding: 1px 5px;
  margin-right: var(--dimension-3);
  margin-bottom: var(--dimension-2);
  color: var(--text-muted);
  background: var(--default-form-element-bg-color);
  border-radius: 4px;
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.orb-users__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 3px;
}

.orb-users__action-btn {
  padding: var(--dimension-3);
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.15s;
}

.orb-users__action-btn--edit:hover {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-users__action-btn--delete:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}

.orb-users__self-dash {
  padding-right: var(--dimension-3);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.users-create__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  min-width: 380px;
}

.users-create__field > * + * {
  margin-top: var(--dimension-3);
}

.users-create__hint {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.users-create__mismatch {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}

.users-create__section {
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.users-create__section > * + * {
  margin-top: 10px;
}

.users-create__section--roles > * + * {
  margin-top: var(--dimension-4);
}

.users-create__checkbox-row {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-4);
}

.users-create__checkbox-hint {
  margin-top: var(--dimension-2);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.users-create__group-label {
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
  color: var(--text-muted);
}

.users-create__error {
  font-size: var(--font-size-normal);
  color: var(--color-light-red-40);
}
</style>
