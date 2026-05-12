<template>
    <OrbModal :open="true" closable @close="$emit('close')">
        <template #header>
            <span class="change-password__title">
                {{ t('userSettings.changePassword') }}
                <span class="change-password__user">{{ userName }}</span>
            </span>
        </template>

        <form class="change-password__form" @submit.prevent="save">
            <div class="change-password__field">
                <CmkLabel>{{ t('userSettings.newPassword') }}</CmkLabel>
                <CmkInput
                    v-model="password"
                    type="password"
                    placeholder="••••••••"
                    field-size="FILL"
                />
            </div>
            <div class="change-password__field">
                <CmkLabel>{{ t('userSettings.confirmPassword') }}</CmkLabel>
                <CmkInput
                    v-model="confirm"
                    type="password"
                    placeholder="••••••••"
                    field-size="FILL"
                />
            </div>

            <p v-if="error" class="change-password__error">{{ error }}</p>
            <p v-if="success" class="change-password__success">
                {{ t('userSettings.passwordChanged') }}
            </p>
        </form>

        <template #footer>
            <CmkButton variant="secondary" @click="$emit('close')">
                {{ success ? t('common.close') : t('common.cancel') }}
            </CmkButton>
            <CmkButton v-if="!success" variant="primary" :disabled="saving" @click="save">
                {{ saving ? t('common.saving') : t('common.save') }}
            </CmkButton>
        </template>
    </OrbModal>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { usersApi } from '@/api/client';
import OrbModal from '@/components/OrbModal.vue';
import { useAuthStore } from '@/stores/auth';

const props = defineProps<{
    userId: number;
    userName: string;
}>();

defineEmits<{ close: [] }>();

const { t } = useI18n();
const auth = useAuthStore();
const password = ref('');
const confirm = ref('');
const saving = ref(false);
const error = ref('');
const success = ref(false);

async function save() {
    error.value = '';
    if (password.value !== confirm.value) {
        error.value = t('userSettings.passwordMismatch');
        return;
    }
    saving.value = true;
    try {
        await usersApi.update(props.userId, { password: password.value }, auth.accessToken!);
        success.value = true;
        // Only refresh own user data — changing another user's password doesn't affect current session
        if (props.userId === auth.user?.user_id) await auth.fetchCurrentUser();
        password.value = '';
        confirm.value = '';
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : t('userSettings.failedToChange');
    } finally {
        saving.value = false;
    }
}
</script>

<style scoped>
.change-password__title {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.change-password__user {
    font-size: var(--font-size-normal);
    font-weight: var(--font-weight-default);
    color: var(--text-muted);
}

.change-password__form {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-5);
    min-width: 320px;
}

.change-password__field {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-3);
}

.change-password__error {
    font-size: var(--font-size-normal);
    color: var(--color-light-red-40);
}

.change-password__success {
    font-size: var(--font-size-normal);
    color: var(--color-corporate-green-50);
}
</style>
