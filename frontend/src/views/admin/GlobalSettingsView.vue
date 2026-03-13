<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">{{ t('settings.title') }}</h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('settings.subtitle') }}</p>
      </div>
      <button @click="handleSave" :disabled="saving"
        class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20">
        {{ saving ? t('common.saving') : t('common.save') }}
      </button>
    </div>

    <div v-if="store.loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else class="space-y-6">

      <!-- Object defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-5">
          {{ t('settings.objectDefaults') }}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">

          <!-- Icon size -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('board.iconSize') }}</span>
            <NumberInput v-model="form.icon_size" min="8" max="256" class="w-24" />
          </label>

          <!-- View type -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.viewType') }}</span>
            <select v-model="form.view_type"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="icon">{{ t('boardSettings.viewTypeIcon') }}</option>
              <option value="text">{{ t('boardSettings.viewTypeText') }}</option>
              <option value="gadget">{{ t('boardSettings.viewTypeGadget') }}</option>
            </select>
          </label>

          <!-- Line type -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.lineStyle') }}</span>
            <select v-model="form.line_style"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option :value="null">{{ t('boardSettings.lineDefault') }}</option>
              <option value="plain">{{ t('boardSettings.lineSimple') }}</option>
              <option value="arrow_end">{{ t('boardSettings.lineArrowRight') }}</option>
              <option value="arrow_start">{{ t('boardSettings.lineArrowLeft') }}</option>
              <option value="arrow_both">{{ t('boardSettings.lineDoubleArrow') }}</option>
              <option value="dashed">{{ t('boardSettings.lineDashed') }}</option>
              <option value="weathermap">{{ t('boardSettings.lineWeathermap') }}</option>
            </select>
          </label>

          <!-- URL target -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.target') }}</span>
            <select v-model="form.url_target"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="_blank">{{ t('boardSettings.targetNewTab') }}</option>
              <option value="_self">{{ t('boardSettings.targetSameTab') }}</option>
              <option value="_top">{{ t('boardSettings.targetTopFrame') }}</option>
            </select>
          </label>

          <!-- Z-index -->
          <div class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.z') }}</span>
            <NumberInput v-model="form.z" min="1" max="999" class="w-20" />
            <p class="text-xs text-zinc-600 mt-1">{{ t('settings.zHint') }}</p>
          </div>

          <!-- Show label -->
          <label class="flex items-center gap-3 cursor-pointer pt-4">
            <input v-model="form.label_show" type="checkbox"
              class="w-4 h-4 rounded accent-indigo-500" />
            <span class="text-sm text-[var(--text)]">{{ t('boardSettings.showLabel') }}</span>
          </label>
        </div>
      </section>

      <!-- Label defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-5">
          {{ t('settings.labelDefaults') }}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">

          <!-- Label size -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.size') }} (px)</span>
            <NumberInput v-model="form.label_size" min="6" max="72" class="w-24" />
          </label>

          <!-- Label color -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.color') }}</span>
            <div class="flex gap-2">
              <input v-model="form.label_color" type="color"
                class="w-10 h-9 rounded cursor-pointer bg-[var(--bg)] border border-[var(--border)]" />
              <input v-model="form.label_color" type="text"
                class="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
            </div>
          </label>

          <!-- Label background -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.background') }}</span>
            <div class="flex gap-2">
              <input v-model="form.label_background" type="color"
                :disabled="form.label_background === 'transparent'"
                class="w-10 h-9 rounded cursor-pointer bg-[var(--bg)] border border-[var(--border)] disabled:opacity-40" />
              <input v-model="form.label_background" type="text"
                placeholder="transparent"
                class="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
            </div>
          </label>

          <!-- Label offset X/Y -->
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.offsetX') }}</span>
              <NumberInput v-model="form.label_x" class="w-24" />
            </label>
            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.offsetY') }}</span>
              <NumberInput v-model="form.label_y" class="w-24" />
            </label>
          </div>
        </div>
      </section>

      <!-- New map defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-5">
          {{ t('settings.newBoardDefaults') }}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">

          <!-- Default backend -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('board.connection') }}</span>
            <select v-model="form.default_backend_id"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
                      <option v-for="b in connectionsStore.backends" :key="b.id" :value="b.id">
                {{ b.label || b.id }}
              </option>
              <option v-if="connectionsStore.backends.length === 0" value="live_1">live_1</option>
            </select>
          </label>

          <!-- Default map type -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('board.boardType') }}</span>
            <select v-model="form.default_map_type"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="static">{{ t('board.boardTypeStatic') }}</option>
              <option value="worldmap">{{ t('board.boardTypeGeoBoard') }}</option>
              <option value="automap">{{ t('board.boardTypeFlowBoard') }}</option>
              <option value="radar">{{ t('board.boardTypeRadar') }}</option>
            </select>
          </label>

          <!-- Hover template -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('settings.hoverTemplate') }}</span>
            <input v-model="form.hover_template" type="text" :placeholder="t('common.noData')"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500" />
          </label>

          <!-- Context template -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('settings.contextTemplate') }}</span>
            <input v-model="form.context_template" type="text" :placeholder="t('common.noData')"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500" />
          </label>
        </div>
      </section>

      <p v-if="saveError" class="text-sm text-red-400">{{ saveError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import NumberInput from '@/components/NumberInput.vue'
import { useSettingsStore } from '@/stores/settings'
import { useConnectionsStore } from '@/stores/connections'
import type { GlobalSettings } from '@/types/api'

const { t } = useI18n()
const store = useSettingsStore()
const connectionsStore = useConnectionsStore()

const form = reactive<GlobalSettings>({ ...store.settings })
const saving = ref(false)
const saveError = ref('')

// Sync form when store finishes loading
watch(
  () => store.settings,
  (val) => Object.assign(form, val),
  { deep: true },
)

async function handleSave() {
  saving.value = true
  saveError.value = ''
  try {
    await store.save({ ...form })
  } catch {
    saveError.value = t('admin.saveFailed')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([store.load(), connectionsStore.fetchBackends()])
  Object.assign(form, store.settings)
})
</script>
