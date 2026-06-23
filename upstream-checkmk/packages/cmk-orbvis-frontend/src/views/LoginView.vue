<template>
  <div class="orb-login">
    <!-- Background -->
    <div class="orb-login__bg">
      <div class="orb-login__glow orb-login__glow--tl" />
      <div class="orb-login__glow orb-login__glow--br" />
      <div class="orb-login__grid" />
    </div>

    <div class="orb-login__panel">
      <!-- Logo -->
      <div class="orb-login__header">
        <div class="orb-login__logo">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
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
        <h1 class="orb-login__title">OrbVis</h1>
        <p class="orb-login__subtitle">
          {{ _t('Monitoring Visualization') }}
        </p>
      </div>

      <!-- Card -->
      <div class="orb-login__card">
        <form class="orb-login__form" @submit.prevent="handleLogin">
          <div class="orb-login__field">
            <label for="login-username" class="orb-login__label">{{ _t('Username') }}</label>
            <CmkInput
              id="login-username"
              v-model="username"
              type="text"
              autocomplete="username"
              :placeholder="_t('Username')"
              field-size="FILL"
            />
          </div>

          <div class="orb-login__field">
            <label for="login-password" class="orb-login__label">{{ _t('Password') }}</label>
            <div class="orb-login__pw-wrap">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="••••••••"
                class="orb-login__pw-input"
                @keydown.enter="handleLogin"
              />
              <button
                type="button"
                class="orb-login__pw-toggle"
                :title="showPassword ? _t('Hide password') : _t('Show password')"
                @click="showPassword = !showPassword"
              >
                <svg
                  v-if="!showPassword"
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
                <svg v-else fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
                  />
                </svg>
              </button>
            </div>
          </div>

          <CmkAlertBox v-if="authStore.error" variant="error">{{ authStore.error }}</CmkAlertBox>

          <!-- CmkButton never triggers a native form submit (the CMK build
               renders @click.prevent, the standalone build type="button"), so
               the click/Enter handlers are the actual login triggers; the
               store's loading guard absorbs any duplicate submit. -->
          <CmkButton
            variant="primary"
            class="orb-login__submit"
            :disabled="authStore.loading"
            @click="handleLogin"
          >
            {{ authStore.loading ? _t('Signing in…') : _t('Sign in') }}
          </CmkButton>
        </form>
      </div>

      <!-- Version footer -->
      <div v-if="capabilities.changelog" class="orb-login__footer">
        <button class="orb-login__version" @click="showChangelog = true">v{{ appVersion }}</button>
      </div>
    </div>

    <ChangelogModal v-if="showChangelog && capabilities.changelog" @close="showChangelog = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import ChangelogModal from '@/components/ChangelogModal.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkButton from '@/components/cmk/CmkButton'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { useAuthStore } from '@/stores/auth'
import { useCapabilitiesStore } from '@/stores/capabilities'
import usei18n from '@cmk/lib/i18n'

const { _t } = usei18n()
const authStore = useAuthStore()
const capabilities = useCapabilitiesStore()
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const showChangelog = ref(false)
const appVersion = __APP_VERSION__

async function handleLogin() {
  authStore.error = null
  await authStore.login(username.value, password.value)
}
</script>

<style scoped>
.orb-login {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  overflow: hidden;
  background: var(--bg);
}

.orb-login__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.orb-login__glow {
  position: absolute;
  width: 550px;
  height: 550px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--color-corporate-green-50) 9%, transparent) 0%,
    transparent 70%
  );
  border-radius: 9999px;
  filter: blur(64px);
}

.orb-login__glow--tl {
  top: -192px;
  left: -192px;
}

.orb-login__glow--br {
  right: -192px;
  bottom: -192px;
}

.orb-login__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(
      color-mix(in srgb, var(--color-corporate-green-50) 3%, transparent) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      color-mix(in srgb, var(--color-corporate-green-50) 3%, transparent) 1px,
      transparent 1px
    );
  background-size: 48px 48px;
}

.orb-login__panel {
  position: relative;
  width: 100%;
  max-width: 440px;
  margin: 0 24px;
}

.orb-login__header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 32px;
}

.orb-login__logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: var(--dimension-6);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
  border-radius: 16px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 40%, transparent);
}

.orb-login__logo svg {
  width: 32px;
  height: 32px;
  color: var(--color-corporate-green-50);
}

.orb-login__title {
  margin-bottom: var(--dimension-3);
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}

.orb-login__subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.orb-login__card {
  padding: 32px;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px rgb(255 255 255 / 8%),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-login__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-7);
}

.orb-login__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.orb-login__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
}

.orb-login__pw-wrap {
  display: flex;
  align-items: center;
  width: 100%;
  background: var(--bg-input, var(--bg-surface));
  border: 1px solid var(--border);
  border-radius: 4px;
  transition: border-color 0.15s;
}

.orb-login__pw-wrap:focus-within {
  border-color: var(--color-corporate-green-50);
}

.orb-login__pw-input {
  flex: 1;
  min-width: 0;
  padding: var(--dimension-3) var(--dimension-4);
  font-size: 13px;
  color: var(--text);
  background: transparent;
  outline: none;
}

.orb-login__pw-input::placeholder {
  color: var(--text-muted);
}

.orb-login__pw-toggle {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  padding: 0 var(--dimension-4);
  color: var(--text-muted);
  transition: color 0.15s;
}

.orb-login__pw-toggle:hover {
  color: var(--text);
}

.orb-login__pw-toggle svg {
  width: 16px;
  height: 16px;
}

.orb-login__submit {
  width: 100%;
}

.orb-login__footer {
  margin-top: var(--dimension-6);
  text-align: center;
}

.orb-login__version {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
