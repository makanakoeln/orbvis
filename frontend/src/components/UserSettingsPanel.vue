<template>
    <OrbModal :open="true" closable @close="tryClose">
        <template #header>
            <span class="user-settings__title">
                {{ isSelf ? t('userSettings.title') : t('admin.editUser', { name: userName }) }}
                <span v-if="isSelf" class="user-settings__user">{{ userName }}</span>
            </span>
        </template>

        <div class="user-settings__body">
            <!-- Admin settings (non-self editing) -->
            <section v-if="!isSelf && userRead" class="user-settings__section">
                <p class="user-settings__section-title">{{ t('admin.settings') }}</p>

                <div class="user-settings__row">
                    <CmkCheckbox v-model="adminIsAdmin" :label="t('admin.administrator')" />
                    <p class="user-settings__hint">{{ t('admin.administratorHint') }}</p>
                </div>

                <CmkCheckbox v-model="adminIsActive" :label="t('admin.active')" />
                <CmkCheckbox v-model="adminMustChange" :label="t('admin.mustChangePassword')" />
            </section>

            <!-- Role assignment (non-self editing) -->
            <section
                v-if="!isSelf && userRead && availableRoles?.length"
                class="user-settings__section user-settings__section--divided"
            >
                <p class="user-settings__section-title">{{ t('admin.roles') }}</p>
                <div v-for="role in availableRoles" :key="role.role_id">
                    <CmkCheckbox
                        :model-value="adminRoleIds.includes(role.role_id)"
                        :label="role.name"
                        @update:model-value="
                            (v) => {
                                if (v) adminRoleIds.push(role.role_id);
                                else
                                    adminRoleIds = adminRoleIds.filter((id) => id !== role.role_id);
                            }
                        "
                    />
                </div>
            </section>

            <!-- Theme selector (only for self) -->
            <section v-if="isSelf" class="user-settings__section">
                <CmkLabel>{{ t('userSettings.theme') }}</CmkLabel>
                <div class="user-settings__toggle-group">
                    <button
                        v-for="opt in themeOptions"
                        :key="opt.value"
                        type="button"
                        class="user-settings__toggle"
                        :class="{ 'user-settings__toggle--active': selectedTheme === opt.value }"
                        @click="selectTheme(opt.value)"
                    >
                        <component :is="opt.icon" class="user-settings__toggle-icon" />
                        {{ opt.label }}
                    </button>
                </div>
            </section>

            <!-- Language selector -->
            <section
                v-if="isSelf && !auth.ssoActive && !auth.isCheckmkDeployment"
                class="user-settings__section"
            >
                <CmkLabel>{{ t('userSettings.language') }}</CmkLabel>
                <div class="user-settings__toggle-group">
                    <button
                        v-for="opt in languageOptions"
                        :key="opt.value"
                        type="button"
                        class="user-settings__toggle"
                        :class="{ 'user-settings__toggle--active': selectedLanguage === opt.value }"
                        @click="selectedLanguage = opt.value"
                    >
                        {{ opt.label }}
                    </button>
                </div>
            </section>

            <!-- Password change -->
            <section
                v-if="showPasswordSection"
                class="user-settings__section"
                :class="{ 'user-settings__section--divided': isSelf }"
            >
                <p class="user-settings__section-title">{{ t('userSettings.changePassword') }}</p>
                <form class="user-settings__pw-form" @submit.prevent="savePassword">
                    <div class="user-settings__pw-field">
                        <CmkLabel>{{ t('userSettings.newPassword') }}</CmkLabel>
                        <CmkInput
                            v-model="password"
                            type="password"
                            autocomplete="new-password"
                            field-size="FILL"
                        />
                        <p class="user-settings__hint">
                            {{ t('userSettings.passwordMinLength') }}
                        </p>
                    </div>
                    <div class="user-settings__pw-field">
                        <CmkLabel>{{ t('userSettings.confirmPassword') }}</CmkLabel>
                        <CmkInput
                            v-model="confirm"
                            type="password"
                            autocomplete="new-password"
                            field-size="FILL"
                        />
                    </div>

                    <p v-if="pwError" class="user-settings__error">{{ pwError }}</p>
                    <p v-if="pwSuccess" class="user-settings__success">
                        {{ t('userSettings.passwordChanged') }}
                    </p>

                    <div v-if="!pwSuccess" class="user-settings__pw-actions">
                        <CmkButton variant="secondary" :disabled="pwSaving" @click="savePassword">
                            {{
                                pwSaving ? t('common.saving') : t('userSettings.changePasswordBtn')
                            }}
                        </CmkButton>
                    </div>
                </form>
            </section>

            <!-- Tour reset (self only) -->
            <section v-if="isSelf" class="user-settings__section user-settings__section--divided">
                <p v-if="tourResetDone" class="user-settings__success">
                    {{ t('userSettings.tourResetDone') }}
                </p>
                <CmkButton v-else variant="secondary" @click="resetTour">
                    {{ t('userSettings.resetTour') }}
                </CmkButton>
            </section>

            <!-- Save error -->
            <p v-if="saveError || adminError" class="user-settings__error">
                {{ saveError || adminError }}
            </p>

            <!-- Unsaved-changes warning -->
            <CmkAlertBox v-if="showUnsavedWarning" variant="warning" size="small">
                {{ t('userSettings.unsavedChanges') }}
                <CmkButton variant="secondary" @click="discardAndClose">
                    {{ t('common.discard') }}
                </CmkButton>
            </CmkAlertBox>
        </div>

        <template v-if="isSelf || (!isSelf && userRead)" #footer>
            <CmkButton variant="secondary" @click="discardAndClose">
                {{ t('common.cancel') }}
            </CmkButton>
            <CmkButton
                variant="primary"
                :disabled="isSelf ? saving || !isDirty : adminSaving"
                @click="isSelf ? save() : saveAdminSettings()"
            >
                {{ (isSelf ? saving : adminSaving) ? t('common.saving') : t('common.save') }}
            </CmkButton>
        </template>
    </OrbModal>
</template>

<script setup lang="ts">
import { computed, h, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { usersApi } from '@/api/client';
import CmkAlertBox from '@/components/cmk/CmkAlertBox';
import CmkButton from '@/components/cmk/CmkButton';
import CmkLabel from '@/components/cmk/CmkLabel';
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import OrbModal from '@/components/OrbModal.vue';
import { applyTheme } from '@/composables/useTheme';
import { i18n } from '@/i18n';
import { useAuthStore } from '@/stores/auth';
import type { RoleRead, UserRead } from '@/types/api';

const { t } = useI18n();

const props = defineProps<{
    userId: number;
    userName: string;
    isSelf: boolean;
    userRead?: UserRead;
    availableRoles?: RoleRead[];
}>();

const emit = defineEmits<{ close: [] }>();

const auth = useAuthStore();

// ---- Admin settings (non-self) ----

const adminIsAdmin = ref(props.userRead?.is_admin ?? false);
const adminIsActive = ref(props.userRead?.is_active ?? true);
const adminMustChange = ref(props.userRead?.must_change_password ?? false);
const adminRoleIds = ref<number[]>(props.userRead?.roles.map((r) => r.role_id) ?? []);
const adminSaving = ref(false);
const adminError = ref('');

async function saveAdminSettings() {
    adminSaving.value = true;
    adminError.value = '';
    try {
        await usersApi.update(
            props.userId,
            {
                is_admin: adminIsAdmin.value,
                is_active: adminIsActive.value,
                must_change_password: adminMustChange.value,
            },
            auth.accessToken!,
        );
        const currentIds = props.userRead?.roles.map((r) => r.role_id) ?? [];
        const toAdd = adminRoleIds.value.filter((id) => !currentIds.includes(id));
        const toRemove = currentIds.filter((id) => !adminRoleIds.value.includes(id));
        await Promise.all([
            ...toAdd.map((rid) => usersApi.assignRole(props.userId, rid, auth.accessToken!)),
            ...toRemove.map((rid) => usersApi.removeRole(props.userId, rid, auth.accessToken!)),
        ]);
        emit('close');
    } catch (e: unknown) {
        adminError.value = e instanceof Error ? e.message : 'Save failed.';
    } finally {
        adminSaving.value = false;
    }
}

// ---- Theme ----

const savedTheme = ref(auth.user?.theme ?? 'system');
const selectedTheme = ref(auth.user?.theme ?? 'system');

// ---- Language ----

const savedLanguage = ref(auth.user?.language ?? 'en');
const selectedLanguage = ref(auth.user?.language ?? 'en');

const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'de', label: 'Deutsch' },
];

const isDirty = computed(
    () =>
        selectedTheme.value !== savedTheme.value || selectedLanguage.value !== savedLanguage.value,
);
const showUnsavedWarning = ref(false);
const saving = ref(false);
const saveError = ref('');

const SunIcon = () =>
    h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
        h('path', {
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round',
            d: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z',
        }),
    ]);
const MoonIcon = () =>
    h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
        h('path', {
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round',
            d: 'M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z',
        }),
    ]);
const SystemIcon = () =>
    h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
        h('path', {
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round',
            d: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
        }),
    ]);

const themeOptions = computed(() => [
    { value: 'dark', label: t('userSettings.themeDark'), icon: MoonIcon },
    { value: 'light', label: t('userSettings.themeLight'), icon: SunIcon },
    { value: 'system', label: t('userSettings.themeAuto'), icon: SystemIcon },
]);

function selectTheme(theme: string) {
    selectedTheme.value = theme;
    showUnsavedWarning.value = false;
    if (props.isSelf) applyTheme(theme, auth.ssoActive, auth.user?.cmk_theme);
}

async function save() {
    saving.value = true;
    saveError.value = '';
    try {
        await usersApi.update(
            props.userId,
            { theme: selectedTheme.value, language: selectedLanguage.value },
            auth.accessToken!,
        );
        savedTheme.value = selectedTheme.value;
        savedLanguage.value = selectedLanguage.value;
        if (props.isSelf) {
            i18n.global.locale.value = selectedLanguage.value as 'en' | 'de';
            await auth.fetchCurrentUser();
        }
        showUnsavedWarning.value = false;
        emit('close');
    } catch (e: unknown) {
        saveError.value = e instanceof Error ? e.message : 'Save failed.';
    } finally {
        saving.value = false;
    }
}

function tryClose() {
    if (props.isSelf && isDirty.value) {
        showUnsavedWarning.value = true;
    } else {
        emit('close');
    }
}

function discardAndClose() {
    if (props.isSelf) applyTheme(savedTheme.value, auth.ssoActive, auth.user?.cmk_theme);
    selectedTheme.value = savedTheme.value;
    selectedLanguage.value = savedLanguage.value;
    emit('close');
}

// ---- Tour reset ----

const tourResetDone = ref(false);

function resetTour() {
    localStorage.removeItem(`orbvis_onboarded_${props.userId}`);
    localStorage.removeItem(`orbvis_board_toured_${props.userId}`);
    tourResetDone.value = true;
}

// ---- Password ----

const showPasswordSection = computed(
    () => !(props.isSelf && (auth.ssoActive || auth.isCheckmkDeployment)),
);

const password = ref('');
const confirm = ref('');
const pwSaving = ref(false);
const pwError = ref('');
const pwSuccess = ref(false);

async function savePassword() {
    pwError.value = '';
    if (password.value !== confirm.value) {
        pwError.value = t('userSettings.passwordMismatch');
        return;
    }
    pwSaving.value = true;
    try {
        await usersApi.update(props.userId, { password: password.value }, auth.accessToken!);
        pwSuccess.value = true;
        if (props.isSelf) await auth.fetchCurrentUser();
        password.value = '';
        confirm.value = '';
    } catch (e: unknown) {
        pwError.value = e instanceof Error ? e.message : t('userSettings.failedToChange');
    } finally {
        pwSaving.value = false;
    }
}
</script>

<style scoped>
.user-settings__title {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.user-settings__user {
    font-size: var(--font-size-normal);
    font-weight: var(--font-weight-default);
    color: var(--text-muted);
}

.user-settings__body {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-5);
    min-width: 300px;
}

.user-settings__section {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-4);
}

.user-settings__section--divided {
    padding-top: var(--dimension-5);
    border-top: 1px solid var(--border);
}

.user-settings__section-title {
    font-size: var(--font-size-large);
    font-weight: 500;
    color: var(--text-muted);
}

.user-settings__row {
    display: flex;
    align-items: flex-start;
    gap: var(--dimension-4);
}

.user-settings__hint {
    font-size: var(--font-size-normal);
    color: var(--text-muted);
    margin-top: 2px;
}

.user-settings__toggle-group {
    display: flex;
    gap: var(--dimension-3);
    margin-top: var(--dimension-3);
}

.user-settings__toggle {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--dimension-3);
    padding: var(--dimension-4) var(--dimension-5);
    border-radius: var(--dimension-3);
    background: var(--default-form-element-bg-color);
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: var(--font-size-normal);
    font-weight: 500;
    cursor: pointer;
}

.user-settings__toggle:hover {
    color: var(--text);
}

.user-settings__toggle--active {
    background: var(--toggle-button-group-active-bg-color);
    color: var(--text);
}

.user-settings__toggle-icon {
    width: 13px;
    height: 13px;
}

.user-settings__pw-form {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-4);
}

.user-settings__pw-field {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-3);
}

.user-settings__pw-actions {
    display: flex;
    justify-content: flex-end;
}

.user-settings__error {
    font-size: var(--font-size-normal);
    color: var(--color-light-red-40);
}

.user-settings__success {
    font-size: var(--font-size-normal);
    color: var(--color-corporate-green-50);
}
</style>
