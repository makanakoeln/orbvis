<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl p-6 w-[26rem] space-y-4">
        <h3 class="text-base font-bold text-[var(--text)]">{{ t('downtime.title') }}</h3>
        <p class="text-xs text-[var(--text-muted)] -mt-2">{{ displayName }}</p>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{ t('downtime.startTime') }}</label>
            <input v-model="startTime" type="datetime-local"
              class="w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{ t('downtime.endTime') }}</label>
            <input v-model="endTime" type="datetime-local"
              class="w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{ t('downtime.comment') }}</label>
            <input v-model="comment"
              class="w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              :placeholder="t('downtime.comment') + '…'"
              @keydown.esc="$emit('close')" />
          </div>
        </div>

        <p v-if="error" class="text-xs text-red-400">{{ error }}</p>
        <p v-if="success" class="text-xs text-green-400">{{ t('downtime.success') }}</p>

        <div class="flex gap-3 justify-end pt-1 border-t border-[var(--border)]">
          <button @click="$emit('close')"
            class="px-4 py-2 rounded-lg text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">
            {{ t('common.cancel') }}
          </button>
          <button @click="submit" :disabled="submitting || !comment.trim()"
            class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-white transition-all">
            {{ submitting ? t('downtime.submitting') : t('downtime.submit') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { BoardObject } from '@/types/api'
import { cmkApi } from '@/api/client'

const { t } = useI18n()

const props = defineProps<{
  object: BoardObject
  checkmkUrl: string
}>()

const emit = defineEmits<{ close: [] }>()

function toLocalDatetimeString(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const now = new Date()
const oneHourLater = new Date(now.getTime() + 3600_000)

const startTime = ref(toLocalDatetimeString(now))
const endTime = ref(toLocalDatetimeString(oneHourLater))
const comment = ref('')
const submitting = ref(false)
const error = ref('')
const success = ref(false)

const displayName = computed(() => {
  if (props.object.host_name && props.object.service_description)
    return `${props.object.host_name} / ${props.object.service_description}`
  return props.object.host_name ?? props.object.group_name ?? props.object.id
})

async function submit() {
  if (!comment.value.trim() || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const start = new Date(startTime.value).toISOString()
    const end = new Date(endTime.value).toISOString()
    if (props.object.type === 'service' && props.object.host_name && props.object.service_description) {
      await cmkApi.downtimeService(
        props.checkmkUrl,
        props.object.host_name,
        props.object.service_description,
        start,
        end,
        comment.value,
      )
    } else if (props.object.host_name) {
      await cmkApi.downtimeHost(
        props.checkmkUrl,
        props.object.host_name,
        start,
        end,
        comment.value,
      )
    }
    success.value = true
    setTimeout(() => emit('close'), 1200)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t('downtime.error')
  } finally {
    submitting.value = false
  }
}
</script>
