<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-[26rem]">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-base font-bold text-[var(--text)]">{{ t('admin.createBoard') }}</h3>
          <button @click="$emit('close')"
            class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form @submit.prevent="submit" class="space-y-4">
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              {{ t('admin.boardId') }}
            </label>
            <input :value="form.name" @input="onNameInput" placeholder="my-board" required
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 transition-all"
              :class="nameError ? 'ring-red-500/60 focus:ring-red-500' : 'ring-zinc-700 focus:ring-indigo-500'" />
            <p v-if="nameError" class="text-xs text-red-400">{{ nameError }}</p>
            <p v-else class="text-xs text-zinc-600">{{ t('admin.boardIdHint') }}</p>
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('admin.alias') }}</label>
            <input v-model="form.alias" placeholder="My Board"
              @input="aliasTouched = true"
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.connection') }}</label>
            <div class="relative">
              <select v-model="form.backend_id" required
                class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                <option value="" disabled>{{ t('admin.selectConnection') }}</option>
                <option v-for="b in connectionsStore.backends" :key="b.id" :value="b.id">
                  {{ b.label || b.id }}
                </option>
              </select>
              <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                </svg>
              </div>
            </div>
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.boardType') }}</label>
            <div class="relative">
              <select v-model="form.view_type"
                class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                <option value="static">{{ t('board.boardTypeStatic') }}</option>
                <option value="worldmap">{{ t('board.boardTypeGeoBoard') }}</option>
                <option value="automap">{{ t('board.boardTypeFlowBoard') }}</option>
                <option value="radar">{{ t('board.boardTypeRadar') }}</option>
              </select>
              <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                </svg>
              </div>
            </div>
            <p class="text-xs text-zinc-500">
              <template v-if="form.view_type === 'static'">{{ t('board.boardTypeStaticDesc') }}</template>
              <template v-else-if="form.view_type === 'worldmap'">{{ t('board.boardTypeGeoBoardDesc') }}</template>
              <template v-else-if="form.view_type === 'automap'">{{ t('board.boardTypeFlowBoardDesc') }}</template>
              <template v-else-if="form.view_type === 'radar'">{{ t('board.boardTypeRadarDesc') }}</template>
            </p>
          </div>
          <div class="flex gap-3 justify-end pt-2 border-t border-[var(--border)]">
            <button type="button" @click="$emit('close')"
              class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">
              {{ t('common.cancel') }}
            </button>
            <button type="submit" :disabled="!form.name || !!nameError"
              class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-white transition-all">
              {{ t('common.create') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBoardsStore } from '@/stores/boards'
import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import { sanitizeBoardName, slugToTitleCase } from '@/utils/naming'

const emit = defineEmits<{ close: []; created: [name: string] }>()

const { t } = useI18n()
const boardsStore = useBoardsStore()
const connectionsStore = useConnectionsStore()
const settingsStore = useSettingsStore()

const form = ref({ name: '', alias: '', backend_id: '', view_type: 'static' })
const aliasTouched = ref(false)

const _NAME_RE = /^[a-zA-Z0-9_-]+$/
const nameError = computed(() => {
  if (!form.value.name) return ''
  if (!_NAME_RE.test(form.value.name)) return t('admin.boardIdInvalid')
  return ''
})

function onNameInput(e: Event) {
  form.value.name = sanitizeBoardName((e.target as HTMLInputElement).value)
  if (!aliasTouched.value) {
    form.value.alias = slugToTitleCase(form.value.name)
  }
}

onMounted(async () => {
  await Promise.all([connectionsStore.fetchBackends(), settingsStore.load()])
  form.value.backend_id = settingsStore.settings.default_backend_id || connectionsStore.backends[0]?.id || ''
  form.value.view_type = settingsStore.settings.default_map_type || 'static'
})

async function submit() {
  await boardsStore.createBoard(form.value.name, form.value.alias, form.value.backend_id, form.value.view_type, settingsStore.settings.icon_size)
  const created = form.value.name
  form.value = {
    name: '',
    alias: '',
    backend_id: settingsStore.settings.default_backend_id || connectionsStore.backends[0]?.id || '',
    view_type: settingsStore.settings.default_map_type || 'static',
  }
  emit('created', created)
}
</script>
