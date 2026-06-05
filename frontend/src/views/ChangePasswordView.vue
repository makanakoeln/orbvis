<template>
  <div class="orb-pwchange">
    <div class="orb-pwchange__panel">
      <div class="orb-pwchange__header">
        <div class="orb-pwchange__icon">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z"
            />
          </svg>
        </div>
        <h1 class="orb-pwchange__title">
          {{ t('changePassword.title') }}
        </h1>
        <p class="orb-pwchange__subtitle">
          {{ t('changePassword.subtitle') }}
        </p>
      </div>

      <div class="orb-pwchange__card">
        <form class="orb-pwchange__form" @submit.prevent="save">
          <div class="orb-pwchange__field">
            <label class="orb-pwchange__label">{{ t('changePassword.newPassword') }}</label>
            <input
              v-model="password"
              type="password"
              placeholder="••••••••"
              required
              minlength="6"
              autofocus
              class="orb-field orb-pwchange__input"
            />
          </div>
          <div class="orb-pwchange__field">
            <label class="orb-pwchange__label">{{ t('changePassword.confirmPassword') }}</label>
            <input
              v-model="confirm"
              type="password"
              placeholder="••••••••"
              required
              class="orb-field orb-pwchange__input"
            />
          </div>

          <p v-if="error" class="orb-pwchange__error">{{ error }}</p>

          <button type="submit" :disabled="saving" class="orb-pwchange__submit">
            {{ saving ? t('common.saving') : t('changePassword.setNewPassword') }}
          </button>
        </form>
      </div>

      <p class="orb-pwchange__footer">
        {{ t('changePassword.loggedInAs') }}
        <span class="orb-pwchange__user">{{ auth.user?.name }}</span> ·
        <button class="orb-pwchange__logout" @click="auth.logout">
          {{ t('auth.logout') }}
        </button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { usersApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const password = ref('')
const confirm = ref('')
const saving = ref(false)
const error = ref('')

async function save() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = t('changePassword.passwordMismatch')
    return
  }
  saving.value = true
  try {
    await usersApi.update(auth.user!.user_id, { password: password.value }, auth.accessToken!)
    await auth.fetchCurrentUser()
    router.push({ name: 'home' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t('changePassword.failedToChange')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.orb-pwchange {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--dimension-6);
  background: var(--bg);
}

.orb-pwchange__panel {
  width: 100%;
  max-width: 384px;
}

.orb-pwchange__header {
  margin-bottom: 32px;
  text-align: center;
}

.orb-pwchange__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin: 0 auto var(--dimension-6);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  border-radius: 16px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 25%, transparent);
}

.orb-pwchange__icon svg {
  width: 24px;
  height: 24px;
  color: var(--color-yellow-50);
}

.orb-pwchange__title {
  font-size: 20px;
  line-height: 28px;
  font-weight: 700;
  color: var(--text);
}

.orb-pwchange__subtitle {
  margin-top: 6px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-pwchange__card {
  padding: var(--dimension-8);
  background: var(--bg-surface);
  border-radius: 16px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 50%);
}

.orb-pwchange__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

.orb-pwchange__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.orb-pwchange__label {
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
  color: var(--text-muted);
}

.orb-pwchange__input {
  padding: 10px 14px;
}

.orb-pwchange__error {
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--color-light-red-40);
}

.orb-pwchange__submit {
  width: 100%;
  padding: 10px 0;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 600;
  color: var(--button-primary-text-color, #000);
  background: var(--color-corporate-green-50);
  border-radius: 8px;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-pwchange__submit:hover {
  background: var(--color-corporate-green-60);
}

.orb-pwchange__submit:disabled {
  opacity: 0.5;
}

.orb-pwchange__footer {
  margin-top: var(--dimension-6);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
  text-align: center;
}

.orb-pwchange__user {
  color: var(--text-muted);
}

.orb-pwchange__logout {
  color: var(--text-muted);
}
</style>
