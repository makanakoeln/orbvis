<template>
    <div
        class="min-h-screen flex items-center justify-center bg-[var(--bg)] relative overflow-hidden"
    >
        <!-- Background -->
        <div class="absolute inset-0 pointer-events-none">
            <div
                class="absolute -top-48 -left-48 w-[600px] h-[600px] rounded-full blur-3xl"
                style="
                    background: radial-gradient(circle, rgb(21 209 160 / 12%) 0%, transparent 70%);
                "
            />
            <div
                class="absolute -bottom-48 -right-48 w-[500px] h-[500px] rounded-full blur-3xl"
                style="
                    background: radial-gradient(circle, rgb(21 209 160 / 6%) 0%, transparent 70%);
                "
            />
            <div
                class="absolute inset-0"
                style="
                    background-image:
                        linear-gradient(rgb(21 209 160 / 3%) 1px, transparent 1px),
                        linear-gradient(90deg, rgb(21 209 160 / 3%) 1px, transparent 1px);
                    background-size: 48px 48px;
                "
            />
        </div>

        <div class="relative w-full max-w-[440px] mx-[24px]">
            <!-- Logo -->
            <div class="flex flex-col items-center mb-[32px]">
                <div
                    class="inline-flex items-center justify-center w-[64px] h-[64px] bg-[rgb(21_209_160/10%)] ring-1 ring-[var(--color-corporate-green-50)]/40 rounded-2xl mb-[16px]"
                >
                    <svg
                        class="w-[32px] h-[32px] text-[var(--color-corporate-green-50)]"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="1.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M2 12C5.5 6.5 18.5 6.5 22 12C18.5 17.5 5.5 17.5 2 12Z"
                        />
                        <circle cx="12" cy="12" r="3.5" />
                        <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
                        <circle cx="13.8" cy="10.2" r="0.6" fill="currentColor" stroke="none" />
                    </svg>
                </div>
                <h1 class="font-bold text-[22px] text-[var(--text)] mb-[4px]">OrbVis</h1>
                <p class="text-[13px] text-[var(--text-muted)]">
                    {{ t('auth.monitoringVisualization') }}
                </p>
            </div>

            <!-- Card -->
            <div
                class="bg-[var(--bg-surface)] ring-1 ring-white/8 shadow-2xl shadow-black/60 rounded-xl p-[32px]"
            >
                <form class="flex flex-col gap-[20px]" @submit.prevent="handleLogin">
                    <div class="flex flex-col gap-[6px]">
                        <label
                            for="login-username"
                            class="font-medium text-[13px] text-[var(--text)]"
                            >{{ t('auth.username') }}</label
                        >
                        <CmkInput
                            id="login-username"
                            v-model="username"
                            type="text"
                            autocomplete="username"
                            :placeholder="t('auth.username')"
                            field-size="FILL"
                        />
                    </div>

                    <div class="flex flex-col gap-[6px]">
                        <label
                            for="login-password"
                            class="font-medium text-[13px] text-[var(--text)]"
                            >{{ t('auth.password') }}</label
                        >
                        <div
                            class="flex items-center w-full rounded-[4px] border border-[var(--border)] bg-[var(--bg-input,var(--bg-surface))] focus-within:border-[var(--color-corporate-green-50)] transition-colors"
                        >
                            <input
                                id="login-password"
                                v-model="password"
                                :type="showPassword ? 'text' : 'password'"
                                autocomplete="current-password"
                                placeholder="••••••••"
                                class="flex-1 min-w-0 bg-transparent px-[8px] py-[4px] text-[13px] text-[var(--text)] placeholder-[var(--text-muted)] outline-none"
                                @keydown.enter="handleLogin"
                            />
                            <button
                                type="button"
                                class="shrink-0 flex items-center px-2 text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
                                :title="
                                    showPassword ? t('auth.hidePassword') : t('auth.showPassword')
                                "
                                @click="showPassword = !showPassword"
                            >
                                <svg
                                    v-if="!showPassword"
                                    class="w-4 h-4"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
                                    />
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                    />
                                </svg>
                                <svg
                                    v-else
                                    class="w-4 h-4"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
                                    />
                                </svg>
                            </button>
                        </div>
                    </div>

                    <CmkAlertBox v-if="authStore.error" variant="error">{{
                        authStore.error
                    }}</CmkAlertBox>

                    <CmkButton
                        variant="primary"
                        class="w-full"
                        :disabled="authStore.loading"
                        @click="handleLogin"
                    >
                        {{ authStore.loading ? t('auth.signingIn') : t('auth.signIn') }}
                    </CmkButton>
                </form>
            </div>

            <!-- Version footer -->
            <div class="text-center mt-[16px]">
                <button
                    class="text-[12px] text-zinc-600 hover:text-zinc-400 transition-colors"
                    @click="showChangelog = true"
                >
                    v{{ appVersion }}
                </button>
            </div>
        </div>

        <ChangelogModal v-if="showChangelog" @close="showChangelog = false" />
    </div>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import ChangelogModal from '@/components/ChangelogModal.vue';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const authStore = useAuthStore();
const username = ref('');
const password = ref('');
const showPassword = ref(false);
const showChangelog = ref(false);
const appVersion = __APP_VERSION__;

async function handleLogin() {
    authStore.error = null;
    await authStore.login(username.value, password.value);
}
</script>
